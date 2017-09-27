""" The main content model """

import logging

from django_extensions.db.fields import AutoSlugField
from model_utils.models import TimeStampedModel
from slugify import Slugify

from apps.contributors.models import Contributor
from apps.frontpage.models import FrontpageStory
from apps.markup.models import Alias
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from utils.model_mixins import EditURLMixin

from .byline import Byline, clean_up_bylines
from .mixins import MarkupCharField, MarkupTextField, TextContent
from .place_inlines import InlineElementsMixin
from .sections import StoryType, default_story_type
from .storychildren import Aside, Pullquote, StoryImage

slugify = Slugify(max_length=50, to_lower=True)
logger = logging.getLogger(__name__)


class StoryQuerySet(models.QuerySet):
    def published(self):
        now = timezone.now()
        return self.filter(
            publication_status__in=[
                Story.STATUS_PUBLISHED,
                Story.STATUS_NOINDEX,
            ]
        ).filter(publication_date__lt=now
                 ).select_related('story_type__section')

    def is_on_frontpage(self, frontpage):
        return self.filter(frontpagestory__placements=frontpage)


class PublishedStoryManager(models.Manager):
    def get_queryset(self):
        return StoryQuerySet(self.model, using=self._db)

    def published(self):
        return self.get_queryset().published()

    def is_on_frontpage(self, frontpage):
        return self.get_queryset().is_on_frontpage(frontpage)

    def populate_frontpage(self, **kwargs):
        """ create some random frontpage stories """
        if not kwargs:
            this_year = timezone.now().year
            kwargs = {'publication_date__year': this_year}
        new_stories = self.filter(**kwargs).order_by('publication_date')
        for story in new_stories:
            story.frontpagestory_set.all().delete()
            story.save(new=True)

    def devalue_hotness(self, factor=0.99):
        """ Devalue hot count for all stories. Run as a scheduled task. """
        hot_stories = self.exclude(hot_count__lt=1)
        hot_stories.update(hot_count=(models.F('hot_count') - 1) * factor)


class Story(
    EditURLMixin,
    TimeStampedModel,
    TextContent,
    InlineElementsMixin,
):
    """ An article or story in the newspaper. """

    class Meta:
        verbose_name = _('Story')
        verbose_name_plural = _('Stories')

    objects = PublishedStoryManager()
    template_name = 'bodytext.html'

    STATUS_DRAFT = 0
    STATUS_JOURNALIST = 3
    STATUS_SUBEDITOR = 4
    STATUS_EDITOR = 5
    STATUS_TO_DESK = 6
    STATUS_AT_DESK = 7
    STATUS_FROM_DESK = 9
    STATUS_PUBLISHED = 10
    STATUS_NOINDEX = 11
    STATUS_PRIVATE = 15
    STATUS_TEMPLATE = 100
    STATUS_ERROR = 500
    STATUS_CHOICES = [
        (STATUS_DRAFT, _('Draft')),
        (STATUS_JOURNALIST, _('To Journalist')),
        (STATUS_SUBEDITOR, _('To Sub Editor')),
        (STATUS_EDITOR, _('To Editor')),
        (STATUS_TO_DESK, _('Ready for newsdesk')),
        (STATUS_AT_DESK, _('Imported to newsdesk')),
        (STATUS_FROM_DESK, _('Exported from newsdesk')),
        (STATUS_PUBLISHED, _('Published on website')),
        (STATUS_NOINDEX, _('Published, but hidden from search engines')),
        (STATUS_PRIVATE, _('Will not be published')),
        (STATUS_TEMPLATE, _('Used as template for new articles')),
        (STATUS_ERROR, _('Technical error')),
    ]

    prodsak_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        editable=False,
        help_text=_('primary id in the legacy prodsys database.'),
        verbose_name=_('prodsak id')
    )
    language = models.CharField(
        max_length=10,
        help_text=_('language'),
        verbose_name=_('language'),
        choices=settings.LANGUAGES,
        default=settings.LANGUAGES[0][0],
    )
    title = MarkupCharField(
        max_length=1000,
        help_text=_('main headline or title'),
        verbose_name=_('title'),
    )
    slug = AutoSlugField(
        _('slug'),
        default='story-slug',
        allow_duplicates=True,
        populate_from=('title', ),
        max_length=50,
        overwrite=True,
        slugify_function=slugify,
    )
    kicker = MarkupCharField(
        max_length=1000,
        blank=True,
        help_text=_(
            'secondary headline, usually displayed above main headline'
        ),
        verbose_name=_('kicker'),
    )
    lede = MarkupTextField(
        blank=True,
        help_text=_('brief introduction or summary of the story'),
        verbose_name=_('lede'),
    )
    comment = models.TextField(
        default='',
        blank=True,
        help_text=_('for internal use only'),
        verbose_name=_('comment'),
    )
    theme_word = MarkupCharField(
        max_length=100,
        blank=True,
        help_text=_('theme, topic, main keyword'),
        verbose_name=_('theme word'),
    )
    bylines = models.ManyToManyField(
        Contributor,
        through='Byline',
        help_text=_('the people who created this content.'),
        verbose_name=_('bylines'),
    )
    story_type = models.ForeignKey(
        StoryType,
        help_text=_('the type of story.'),
        verbose_name=_('article type'),
        default=default_story_type,
        on_delete=models.SET_DEFAULT,
    )
    publication_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('when this story will be published on the web.'),
        verbose_name=_('publication date'),
    )
    publication_status = models.IntegerField(
        default=STATUS_DRAFT,
        choices=STATUS_CHOICES,
        help_text=_('publication status.'),
        verbose_name=_('status'),
    )
    issue = models.ForeignKey(
        'issues.PrintIssue',
        help_text=_('which issue this story was printed in.'),
        verbose_name=_('issue'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    page = models.IntegerField(
        blank=True,
        null=True,
        help_text=_('which page the story was printed on.'),
        verbose_name=_('page'),
    )
    hit_count = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text=_('how many time the article has been viewed.'),
        verbose_name=_('total page views')
    )
    hot_count = models.PositiveIntegerField(
        default=1000,  # All stories are hot when first published!
        editable=False,
        help_text=_('calculated value representing recent page views.'),
        verbose_name=_('recent page views')
    )
    bylines_html = models.TextField(
        default='',
        editable=False,
        verbose_name=_('all bylines as html.'),
    )
    legacy_html_source = models.TextField(
        blank=True,
        null=True,
        editable=False,
        help_text=_('From old web page. For reference only.'),
        verbose_name=_('Imported html source.'),
    )
    legacy_prodsys_source = models.TextField(
        blank=True,
        null=True,
        editable=False,
        help_text=_('From prodsys. For reference only.'),
        verbose_name=_('Imported xtagged source.'),
    )
    working_title = models.CharField(
        max_length=1000,
        blank=True,
        help_text=_('Working title'),
        verbose_name=_('Working title'),
    )

    def __str__(self):
        title = self.title or f'({self.working_title})' or '[no title]'
        date = self.publication_date
        if date:
            return '{:%Y-%m-%d}: {}'.format(date, title)
        else:
            return title

    def save(self, *args, **kwargs):
        new = kwargs.pop('new', (self.pk is None))
        self.working_title = (
            self.working_title or self.title or f'[{self.story_type}]'
        )

        try:
            old_markup = Story.objects.get(pk=self.pk).bodytext_markup
            if self.bodytext_markup != old_markup:
                self.bodytext_html = ''
        except ObjectDoesNotExist:
            pass

        super().save(*args, **kwargs)

        if new:
            # make inline elements
            self.bodytext_markup = self.place_all_inline_elements()
            super().save(update_fields=['bodytext_markup'])

            if self.frontpagestory_set.count() == 0:
                # make random frontpage story
                FrontpageStory.objects.autocreate(story=self)

    @property
    def parent_story(self):
        # for polymorphism with related content.
        return self

    @property
    def disqus_enabled(self):
        # Is Disqus available here?
        return self.is_published

    @property
    def is_published(self):
        # Is this Story public
        public = [Story.STATUS_NOINDEX, Story.STATUS_PUBLISHED]
        return (
            self.publication_date and self.publication_status in public
            and self.publication_date <= timezone.now()
        )

    @property
    def priority(self):
        """ Calculate a number between 1 and 12 to determine initial
        front page priority. """
        # TODO: Placeholder priority for story.
        pri = 0
        pri += 1 * bool(self.lede)
        pri += 2 * bool(self.main_image())
        pri += 1 * bool(self.kicker)
        pri += 3 * ('@tit' in self.bodytext_markup)
        pri += len(self.bodytext_markup) // 1000
        return min(12, pri)

    def visit_page(self, request):
        """ Check if visit looks like a human and update hit count """
        if not self.is_published:
            # Only count hits on published pages.
            return False
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if not user_agent:
            # Visitor is not using a web browser.
            return False

        bots = ['bot', 'spider', 'yahoo', 'crawler']
        for bot in bots:
            if bot in user_agent:
                # Search engine web crawler.
                return False

        cache_key = '{}{}'.format(
            request.META.get('REMOTE_ADDR', ''),  # visitor ip
            self.pk,  # story primary key
        )
        if cache.get(cache_key):
            # same ip address has visited page recently
            return False

        cache.set(cache_key, 1, 600)  # time to live in seconds is 600

        self.hit_count = models.F('hit_count') + 1
        self.hot_count = models.F('hot_count') + 100
        self.save(update_fields=['hit_count', 'hot_count'])
        return True

    def get_bylines_as_html(self):
        """ create html table of bylines in db for search and admin display """
        # translation.activate(settings.LANGUAGE_CODE)
        all_bylines = ['<table class="admin-bylines">']
        for bl in self.byline_set.select_related('contributor'):
            all_bylines.append(
                '<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
                    bl.get_credit_display(),
                    bl.contributor.display_name,
                    bl.title,
                )
            )
        # translation.deactivate()
        all_bylines.append('</table>')
        return '\n'.join(all_bylines)

    def get_bylines(self):
        # with translation.override()
        # translation.activate(settings.LANGUAGE_CODE)
        authors = []
        for bl in self.byline_set.select_related('contributor'):
            authors.append(
                '{name}{title}'.format(
                    name=bl.contributor.display_name,
                    title=', {}'.format(bl.title) if bl.title else '',
                    # credit=bl.get_credit_display(),
                )
            )
        # translation.deactivate()
        return ', '.join(authors)

    def image_count(self):
        """ Number of story images related to the story """
        return len(self.images())

    def get_images(self):
        ids = self.images().values_list('id', flat=True)
        return StoryImage.objects.filter(id__in=ids)

    def main_image(self):
        """ Get the top image if there is any. """
        top_image = self.images().order_by('-top', 'index').first()
        if top_image:
            return top_image.child

    def facebook_thumb(self):
        if self.main_image():
            imagefile = self.main_image().imagefile
            return imagefile.thumbnail(
                size='800x420',
                crop_box=imagefile.get_crop_box(),
            )

    @property
    def section(self):
        """ Shortcut to related Section """
        return self.story_type.section

    def clear_html(self):
        """ clears html after child is changed """
        if self.bodytext_html != '':
            Aside.objects.filter(parent_story__pk=self.pk).update(
                bodytext_html=''
            )
            Pullquote.objects.filter(parent_story__pk=self.pk).update(
                bodytext_html=''
            )
            self.bodytext_html = ''
            self.save(update_fields=['bodytext_html'])

    def get_absolute_url(self):
        try:
            return reverse(
                viewname='article',
                kwargs={
                    'story_id': str(self.id),
                    'section': self.section.slug,
                    'slug': self.slug,
                }
            )
        except Exception:
            return ''

    def get_shortlink(self):
        url = reverse(
            viewname='article_short',
            kwargs={
                'story_id': str(self.id),
            },
        )
        return url

    def children_modified(self):
        """ check if any related objects have been
        modified after self was last saved. """
        changed_elements = self.storyelement_set.filter(
            modified__gt=self.modified
        )
        changed_links = self.links().filter(modified__gt=self.modified)
        return bool(changed_elements or changed_links)

    def clean(self):
        """ Clean user input and populate fields """
        cleanup = [Story.STATUS_FROM_DESK, Story.STATUS_PUBLISHED]
        published = [Story.STATUS_PUBLISHED, Story.STATUS_NOINDEX]

        if self.publication_status in cleanup:
            if not self.title and '@headline:' not in self.bodytext_markup:
                self.bodytext_markup = self.bodytext_markup.replace(
                    '@tit:', '@headline:', 1
                )
            self.parse_markup()

        self.bodytext_markup = Alias.objects.replace(
            content=self.bodytext_markup, timing=Alias.TIMING_CLEAN
        )

        # self.bodytext_markup = self.reindex_inlines()
        # TODO: Fix redindeksering av placeholders for video og bilder.

        self.bylines_html = self.get_bylines_as_html()
        if self.publication_status in published:
            self.publication_date = self.publication_date or timezone.now()

        # fix tag typos etc.
        super().clean()

    def _block_new(self, tag, content, element):
        """ Add a story element to the main story """
        if element == "byline":
            bylines_raw = clean_up_bylines(content)
            for raw_byline in bylines_raw.splitlines():
                Byline.create(
                    story=self,
                    full_byline=raw_byline,
                    initials='',
                    # TODO: legg inn initialer i bylines som er importert fra
                    # prodsys.
                )
            return self
        elif element == "aside":
            new_element = Aside(parent_story=self, )
        elif element == "pullquote":
            new_element = Pullquote(parent_story=self, )
        return new_element._block_append(tag, content)

    @property
    def tekst(self):
        output = []
        head_tags = [('tit', 'title'), ('ing', 'lede'), ('tema', 'theme_word'),
                     ('stikktit', 'kicker')]
        for tag, attr in head_tags:
            text = getattr(self, attr)
            if text:
                output.append(f'@{tag}:{text}')
        for bl in self.byline_set.all():
            output.append(str(bl))
        output.append(self.bodytext_markup)
        for aside in self.storyelement_set.all():
            if aside._subclass == 'aside':
                output.append(aside.child.bodytext_markup)
        for pullquote in self.storyelement_set.all():
            if pullquote._subclass == 'pullquote':
                output.append(pullquote.child.bodytext_markup)
        return '\n'.join(output)

    @tekst.setter
    def tekst(self, value):
        self.title = ''
        self.lede = ''
        self.theme_word = ''
        self.asides().delete()
        self.pullquotes().delete()
        self.bodytext_markup = value
