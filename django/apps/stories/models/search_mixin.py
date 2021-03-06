from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    SearchVectorField,
    TrigramSimilarity,
)
from django.db.models import (
    Case,
    CharField,
    ExpressionWrapper,
    F,
    FloatField,
    Func,
    Model,
    QuerySet,
    Value,
    When,
)
from django.db.models.functions import Concat
from django.utils.timezone import now


class TrigramWordSimilarity(Func):
    output_field = FloatField()
    function = 'WORD_SIMILARITY'

    def __init__(self, expression, string, **extra):
        if not hasattr(string, 'resolve_expression'):
            string = Value(string)
        super().__init__(string, expression, **extra)


class LogAge(Func):
    """Calculate log 2 of days since datetime column"""
    # Minimum age 1 day. Prevent log of zero error and unintended large
    # effect of log of very small inputs.
    output_field = FloatField()

    template = (
        f'greatest(1.0, log(2::numeric, ('
        'abs(extract(epoch FROM (TIMESTAMP '
        "'%(when)s' - "
        'COALESCE(%(table)s.%(timefield)s,%(table)s.created)'
        '))) / (60 * 60 * 24))::numeric'
        '))'
    )

    # greatest(1.0, log(2, number))
    # return at least 1.0 to avoid zero division or very skewed results
    # for logs close to zero

    # abs(extract(epoch FROM (when - then)))
    # Extract total seconds in timedelta `now - then`
    # `epoch` = 1970-01-01 = unix epoch = total seconds

    # / (60 * 60 * 24)
    # Divide by minutes and seconds and hours: seconds -> days

    # ::numeric
    #  Cast result as `numeric` using PostgreSQL type cast notation
    # `numeric` = decimal type


class FullTextSearchQuerySet(QuerySet):
    """Queryset mixin for performing search and indexing for the Story model"""
    config = 'norwegian'
    case_config = Case(
        When(language='en', then=Value('english')), default=Value(config)
    )
    vector = (
        SearchVector(
            'working_title',
            'title',
            'kicker',
            'theme_word',
            weight='A',
            config=case_config,
        ) + SearchVector(
            'lede',
            weight='B',
            config=case_config,
        ) + SearchVector(
            'bodytext_markup',
            weight='C',
            config=case_config,
        )
    )

    def search(self, query):
        if not isinstance(query, str):
            msg = f'expected query to be str, got {type(query)}, {query!r}'
            raise ValueError(msg)
        result = None
        if len(query) > 5:
            result = self.search_vector_rank(query)
        if not result:
            result = self.trigram_search_rank(query)
        return result.with_age('publication_date').annotate(
            combined_rank=ExpressionWrapper(
                F('rank') / F('age'), FloatField()
            )
        ).order_by('-combined_rank')

    def with_age(self, field='created', when=None):
        if when is None:
            when = now()
        return self.annotate(
            age=LogAge(
                when=when, timefield=field, table=self.model._meta.db_table
            )
        )

    def trigram_search_rank(self, query, cutoff=None):
        """Perform postgresql trigram word similarity lookup"""

        # stricter cutoff for short queries
        if cutoff is None:
            cutoff = 1 - min(5, len(query)) / 10

        head = Concat(
            F('working_title'), Value(' '), F('kicker'), Value(' '),
            F('title'), Value(' '), F('lede')
        )
        ranker = TrigramWordSimilarity(head, query)
        return self.annotate(rank=ranker).filter(rank__gt=cutoff)

    def search_vector_rank(self, query, cutoff=0.2):
        """Perform postgresql full text search using search vector."""
        ranker = SearchRank(
            F('search_vector'), SearchQuery(query, config=self.config)
        )
        return self.annotate(rank=ranker).filter(rank__gt=cutoff)

    def update_search_vector(self):
        """Calculate and store search vector in the database."""
        return self.update(search_vector=self.vector)


class FullTextSearchMixin(Model):

    search_vector = SearchVectorField(
        editable=False,
        null=True,
    )

    class Meta:
        indexes = [
            # Create database index for search vector for improved performance
            GinIndex(fields=['search_vector']),
        ]
        abstract = True
