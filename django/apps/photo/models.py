""" Photography and image files in the publication  """

import logging
import mimetypes
import re
from io import BytesIO
from pathlib import Path
from statistics import median
from typing import Union

import PIL
from model_utils.models import TimeStampedModel
from slugify import Slugify
from sorl import thumbnail
from sorl.thumbnail.images import ImageFile as SorlImageFile

from apps.contributors.models import Contributor
from apps.photo import file_operations
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.search import TrigramSimilarity
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.db import connection, models
# from apps.issues.models import current_issue
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from utils.merge_model_objects import merge_instances
from utils.model_mixins import EditURLMixin

from .cropping.models import AutoCropImage
from .exif import ExifData, exif_to_json, extract_exif_data, prune_exif
from .imagehash import ImageHashModelMixin

logger = logging.getLogger(__name__)

PROFILE_IMAGE_UPLOAD_FOLDER = 'byline-photo'
SIZE_LIMIT = 4_000  # Maximum width or height of uploads
BYTE_LIMIT = 3_000_000  # Maximum filesize of upload or compress

image_file_validator = FileExtensionValidator(['jpg', 'jpeg', 'png'])


class BrokenImage:
    """If thumbnail fails."""
    url = settings.STATIC_URL + 'admin/img/icon-no.svg'

    def read(self):
        return b''


Thumbnail = Union[SorlImageFile, BrokenImage]


def slugify_filename(filename: str) -> Path:
    """make filename url safe and normalized"""
    slugify = Slugify(safe_chars='.-', separator='-')
    fn = Path(filename)
    stem = Path(filename).stem.split('.')[0]
    stem = re.sub(r'-+', '-', slugify(re.sub(r'_.{7}$', '', stem))).strip('-')
    suffix = ''.join(s.lower().replace('jpeg', 'jpg') for s in fn.suffixes)
    return Path(f'{stem}{suffix}')


def upload_image_to(instance: 'ImageFile', filename: str = 'image') -> str:
    """Upload path based on created date and normalized file name"""
    if instance.pk and instance.stem:
        filename = instance.filename  # autogenerate
    return str(instance.upload_folder() / slugify_filename(filename))


class ImageFileQuerySet(models.QuerySet):
    def pending(self):
        return self.filter(cropping_method=self.model.CROP_PENDING)

    def photos(self):
        return self.filter(category=ImageCategoryMixin.PHOTO)

    def illustrations(self):
        return self.filter(category=ImageCategoryMixin.ILLUSTRATION)

    def diagrams(self):
        return self.filter(category=ImageCategoryMixin.DIAGRAM)

    def externals(self):
        return self.filter(category=ImageCategoryMixin.EXTERNAL)

    def profile_images(self):
        return self.filter(category=ImageCategoryMixin.PROFILE)

    def uncategorised(self):
        return self.filter(category=ImageCategoryMixin.UNKNOWN)


def _filter_dupes(dupes, master_hashes, limit=3):
    """Second imagehash comparison pass."""
    diff_pk = []
    for dupe in dupes:
        diffs = [
            val - master_hashes[key] for key, val in dupe.imagehashes.items()
        ]
        diff = median(sorted(diffs)[:3])
        if diff < 8:
            diff_pk.append((diff, dupe.pk))
    if not diff_pk:
        return []
    diff_pk.sort()
    best = diff_pk[0][0] + 0.1
    return [pk for diff, pk in diff_pk if diff / best < 1.5][:limit]


def _get_dupes_raw(qs, ahash, limit=30):
    """Use raw sql to query. This is the only way to use the GIN index."""
    table = ImageFile._meta.db_table
    field = '_imagehash'
    sql = f"""
    SELECT * FROM {table} WHERE {field} %% %(query)s
    ORDER BY similarity({field}, %(query)s ) DESC LIMIT {limit}
    """
    params = {'query': str(ahash)}
    return qs.raw(sql, params)


def _create_gin_index(field='_imagehash', delete=False):
    """Create search index for imagehash."""
    table = ImageFile._meta.db_table
    if delete:
        sql = f'DROP INDEX IF EXISTS {field}_trigram_index;'
    else:
        sql = f'''CREATE INDEX IF NOT EXISTS {field}_trigram_index
                  ON {table} USING GIN ({field} gin_trgm_ops);'''
    with connection.cursor() as cursor:
        cursor.execute(sql)


class ImageFileManager(models.Manager):
    def search(
        self,
        md5=None,
        fingerprint=None,
        filename=None,
        cutoff=0.5,
    ):
        """Search for images matching query."""
        qs = self.get_queryset()
        if md5:
            results = qs.filter(stat__md5=md5)
            if results.count():
                return results
        if fingerprint:
            try:
                master = file_operations.image_from_fingerprint(fingerprint)
            except ValueError as err:
                raise ValueError('incorrect fingerprint: %s' % err) from err
            master_hashes = file_operations.get_imagehashes(master)
            dupes = _get_dupes_raw(qs, master_hashes['ahash'], 30)
            pks = _filter_dupes(dupes, master_hashes)
            return qs.filter(pk__in=pks)

        if filename:
            trigram = TrigramSimilarity('stem', Path(filename).stem)
            return qs.annotate(
                similarity=trigram,
            ).filter(
                similarity__gt=cutoff,
            ).order_by('-similarity')
        return qs.none()

    def filename_search(self, file_name, similarity=0.5):
        """Fuzzy filename search"""
        SQL = '''
        WITH filematches AS (
          SELECT id, SIMILARITY(regexp_replace(original, '.*/', ''), %s)
          AS similarity
          FROM photo_imagefile
        )
        SELECT id from filematches
        WHERE (similarity > %s)
        ORDER BY similarity DESC
        '''
        raw_query = ImageFile.objects.raw(SQL, [file_name, similarity])
        return self.get_queryset().filter(id__in=(im.id for im in raw_query))


class ImageCategoryMixin(models.Model):
    """Sort images by category"""

    class Meta:
        abstract = True

    UNKNOWN = 0
    PHOTO = 1
    ILLUSTRATION = 2
    DIAGRAM = 3
    PROFILE = 4
    EXTERNAL = 5

    CATEGORY_CHOICES = (
        (UNKNOWN, _('unknown')),
        (PHOTO, _('photo')),
        (ILLUSTRATION, _('illustration')),
        (DIAGRAM, _('diagram')),
        (PROFILE, _('profile image')),
        (EXTERNAL, _('third party image')),
    )

    category = models.PositiveSmallIntegerField(
        verbose_name=_('category'),
        help_text=_('category'),
        choices=CATEGORY_CHOICES,
        default=UNKNOWN,
    )

    @property
    def api_category(self):
        """simplified string category for rest api."""
        mapping = {
            self.EXTERNAL: 'photo',
            self.PHOTO: 'photo',
            self.UNKNOWN: 'photo',
            self.PROFILE: 'profile',
            self.DIAGRAM: 'diagram',
            self.ILLUSTRATION: 'illustration',
        }
        return mapping.get(self.category)


class ImageFile(  # type: ignore
    ImageHashModelMixin, TimeStampedModel, EditURLMixin, AutoCropImage,
    ImageCategoryMixin
):
    """Photo or Illustration in the publication."""

    objects = ImageFileManager.from_queryset(ImageFileQuerySet)()

    class Meta:
        verbose_name = _('ImageFile')
        verbose_name_plural = _('ImageFiles')

    stem = models.CharField(
        verbose_name=_('file name stem'),
        max_length=1024,
        blank=True,
    )
    original = thumbnail.ImageField(
        verbose_name=_('original'),
        validators=[image_file_validator],
        upload_to=upload_image_to,
        height_field='full_height',
        width_field='full_width',
        max_length=1024,
        null=True,  # we need pk before we save the image
    )
    full_height = models.PositiveIntegerField(
        verbose_name=_('height'),
        help_text=_('full height in pixels'),
        default=0,
        editable=False,
    )
    full_width = models.PositiveIntegerField(
        verbose_name=_('width'),
        help_text=_('full height in pixels'),
        default=0,
        editable=False,
    )
    old_file_path = models.CharField(
        verbose_name=_('old file path'),
        help_text=_('previous path if the image has been moved.'),
        blank=True,
        null=True,
        editable=False,
        max_length=1000,
    )
    contributor = models.ForeignKey(
        Contributor,
        verbose_name=_('contributor'),
        help_text=_('who made this'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    description = models.CharField(
        verbose_name=_('description'),
        help_text=_('Description of image'),
        default='',
        blank=True,
        null=False,
        max_length=1000,
    )
    copyright_information = models.CharField(
        verbose_name=_('copyright information'),
        help_text=_(
            'extra information about license and attribution if needed.'
        ),
        blank=True,
        null=True,
        max_length=1000,
    )
    exif_data = JSONField(
        verbose_name=_('exif_data'),
        help_text=_('exif_data'),
        default=dict,
        editable=False,
    )

    def __str__(self):
        return self.filename or super(ImageFile, self).__str__()

    def upload_folder(self) -> Path:
        created = self.created or timezone.now()
        return Path(f'{created.year:04}/{created.month:02}/{created.day:02}')

    @property
    def artist(self) -> str:
        """Attribution as string"""
        if self.contributor:
            return f'{self.contributor}'
        return self.copyright_information or '?'

    @artist.setter
    def artist(self, value) -> None:
        if not value:
            self.copyright_information == ''
            self.contributor = None
        else:
            match = Contributor.objects.search(value).first()
            if match:
                self.contributor = match
            else:
                self.copyright_information = value

    @property
    def filename(self) -> str:
        """build a normalized filename"""
        return f'{self.stem}.{(self.pk or 0):0>5}{self.suffix}'

    @property
    def suffix(self) -> str:
        if self.stat.mimetype:
            if self.stat.mimetype == 'image/jpeg':
                return '.jpg'
            return mimetypes.guess_extension(self.stat.mimetype)
        elif self.original:
            return Path(self.original.name).suffix
        else:
            return '.xxx'

    @property
    def small(self) -> Thumbnail:
        return self.thumbnail('200x200')

    @property
    def medium(self) -> Thumbnail:
        return self.thumbnail('800x800', upscale=False)

    @property
    def large(self) -> Thumbnail:
        return self.thumbnail('1500x1500', upscale=False)

    @property
    def preview(self) -> Thumbnail:
        """Return thumb of cropped image"""
        options = dict(crop_box=self.get_crop_box())
        if self.category == ImageFile.DIAGRAM:
            options.update(expand=1)
        if self.category == ImageFile.PROFILE:
            options.update(expand=0.2, colorspace='GRAY')
        return self.thumbnail('150x150', **options)

    @property
    def exif(self) -> ExifData:
        return extract_exif_data(self.exif_data)

    def thumbnail(self, size='x150', **options) -> Thumbnail:
        """Create thumb of image"""
        try:
            return thumbnail.get_thumbnail(self.original, size, **options)
        except Exception:
            logger.exception('Cannot create thumbnail')
            return BrokenImage()

    def is_profile_image(self) -> bool:
        return self.category == ImageFile.PROFILE

    @property
    def is_photo(self) -> bool:
        return self.category not in [ImageFile.DIAGRAM, ImageFile.ILLUSTRATION]

    def build_thumbs(self) -> None:
        """Make sure thumbs exists"""
        self.large
        self.small
        self.preview
        logger.info(f'built thumbs {self}')

    def add_exif_from_file(self, img=None) -> dict:
        if img is None:
            if self.pk:
                src = self.small
            else:
                src = self.original
            img = file_operations.pil_image(src)
        try:
            data = exif_to_json(img)
        except Exception:
            raise
            data = {}

        self.exif_data = data
        if not self.description:
            self.description = self.exif.description
        if not self.copyright_information:
            self.copyright_information = self.exif.copyright
        if self.exif.datetime:
            self.created = self.exif.datetime
        return data

    def delete_thumbnails(self, delete_file=False) -> None:
        """Delete all thumbnails, optinally delete original too"""
        thumbnail.delete(self.original, delete_file=delete_file)

    def similar(self, field='imagehash', minutes=30) -> models.QuerySet:
        """Finds visually simular images using postgresql trigram search."""
        others = ImageFile.objects.exclude(pk=self.pk)
        if field == 'imagehash':
            return others.filter(_imagehash__trigram_similar=self._imagehash)
        if field == 'md5':
            return others.filter(stat__md5=self.stat.md5)
        if field == 'created':
            treshold = timezone.timedelta(minutes=minutes)
            return others.filter(
                created__gt=self.created - treshold,
                created__lt=self.created + treshold,
            )
        else:
            msg = f'field should be imagehash, md5 or created, not {field}'
            raise ValueError(msg)

    def merge_with(self, others):
        """Merge self with duplicate images."""
        # TODO: is `save` needed here?
        merge_instances(self, *list(others)).save()

    def reduce_image_filesize(self, img=None):
        """Remove thumbnail exif from original image"""
        if img is None:
            img = file_operations.pil_image(self.original)

        exif_bytes = prune_exif(img)

        if any([
            img.width > SIZE_LIMIT,
            img.height > SIZE_LIMIT,
            self.original.size > BYTE_LIMIT,
        ]):
            img.thumbnail(
                size=(SIZE_LIMIT, SIZE_LIMIT),
                resample=PIL.Image.LANCZOS,
            )
            resized = True
        else:
            resized = False

        if exif_bytes or resized:
            blob = BytesIO()
            img.save(blob, img.format, exif=exif_bytes, quality=80)
            if self.pk is None:
                self.original.file = ContentFile(blob.getvalue())
            else:
                self.stat.size = self.stat.md5 = None
                self.delete_thumbnails()
                self.original.save(self.filename, blob)
        return img

    def new_image(self):
        """Check image file, compress if needed, and record metadata"""
        img = file_operations.pil_image(self.original)
        if not file_operations.valid_image(img):
            raise ValueError('invalid image file')

        img = file_operations.pil_image(self.original)

        self.stat.mimetype = file_operations.get_mimetype(img)
        self.add_exif_from_file(img)

        img = self.reduce_image_filesize(img)
        self.full_width = img.width
        self.full_height = img.height

    def save(self, *args, **kwargs):
        self.stem = slugify_filename(
            self.stem or Path(self.original.name).stem
        )

        if self.pk is None:
            # make sure image has a id before saving original file
            self.new_image()
            self.build_thumbs()
            original, width, height = (
                self.original, self.full_width, self.full_height
            )
            self.original = None
            self.full_width, self.full_height = width, height
            super().save(*args, **kwargs)  # get id
            # rest framework includes `force_insert=True`, but we only want to
            # use this for the first save, since otherwise the db will complain
            # since the image already has a pk, and this must be unique.
            kwargs.pop('force_insert', '')
            self.original = original
            original.file.name = self.filename

        super().save(*args, **kwargs)


@receiver(models.signals.post_save, sender=ImageFile)
def imagefile_changed(sender, instance, raw, **kwargs):
    """cache buster"""
    nochange = sender.objects.filter(
        pk=instance.pk,
        category=instance.category,
        crop_box=instance.crop_box,
    )
    if raw or nochange:
        return

    assert instance.pk, 'image should have primary key post save'
    from apps.stories.models import Story
    Story.objects.filter(images__imagefile=instance
                         ).update(modified=instance.modified)
    instance.storyimage_set.update(modified=instance.modified)
    instance.person.update(modified=instance.modified)
