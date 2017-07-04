from apps.photo.models import ImageFile
from rest_framework import serializers, viewsets, filters
from rest_framework.exceptions import ValidationError
from apps.photo.cropping.boundingbox import CropBox
from django_filters.rest_framework import DjangoFilterBackend
import json


class jsonDict(dict):
    def __str__(self):
        return json.dumps(self)


class CropBoxField(serializers.Field):

    def to_representation(self, obj):
        return jsonDict(obj.serialize())

    def to_internal_value(self, data):
        try:
            if isinstance(data, str):
                data = json.loads(data)
            return CropBox(**data)
        except (Exception) as err:
            raise ValidationError(str(err)) from err


class ImageFileSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ImageFile
        fields = [
            'id',
            'url',
            'created',
            'cropping_method',
            'method',
            'size',
            'original',
            'thumb',
            'small',
            'large',
            'description',
            'usage',
            '_imagehash',
            'crop_box',
            'is_profile_image',
        ]
        read_only_fields = [
            'original',
        ]

    thumb = serializers.SerializerMethodField()
    original = serializers.SerializerMethodField()
    small = serializers.SerializerMethodField()
    large = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    method = serializers.SerializerMethodField()
    usage = serializers.SerializerMethodField()
    crop_box = CropBoxField()

    def get_usage(self, instance):
        return instance.storyimage_set.count()

    def get_method(self, instance):
        return instance.get_cropping_method_display()

    def get_size(self, instance):
        return [instance.full_width, instance.full_height]

    def _build_uri(self, url):
        return self._context['request'].build_absolute_uri(url)

    def get_original(self, instance):
        return self._build_uri(instance.original.url)

    def get_thumb(self, instance):
        return self._build_uri(instance.preview.url)

    def get_small(self, instance):
        return self._build_uri(instance.small.url)

    def get_large(self, instance):
        return self._build_uri(instance.large.url)


class ImageFileViewSet(viewsets.ModelViewSet):

    """ API endpoint that allows ImageFile to be viewed or updated.  """

    queryset = ImageFile.objects.order_by('-created')
    serializer_class = ImageFileSerializer
    filter_backends = (filters.SearchFilter, DjangoFilterBackend)
    search_fields = ('source_file', 'description')

    def get_queryset(self):
        profile_images = self.request.query_params.get('profile_images', '')
        if profile_images.lower() in ['1', 'yes', 'true']:
            return self.queryset.profile_images()
        elif profile_images.lower() in ['0', 'no', 'false']:
            return self.queryset.photos()
        return self.queryset