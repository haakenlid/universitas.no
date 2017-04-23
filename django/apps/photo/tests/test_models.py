import pytest
from pathlib import Path
from django.core.exceptions import ValidationError
from apps.photo.models import ImageFile
from django.core.files import File
from django.db import transaction


@pytest.fixture
def fixture_image():
    img = Path(__file__).parent / 'fixtureimage.jpg'
    assert img.exists(), 'image not found'
    return str(img)


@pytest.mark.django_db
def test_custom_field(fixture_image):
    img = ImageFile()
    assert img.cropping_method == img.CROP_PENDING
    assert img.crop_box.left < img.crop_box.right
    with open(fixture_image, 'rb') as fp:
        img.source_file.save('foobar.jpg', File(fp))
    img.crop_box.right = 5
    img.crop_box.top = -5
    img.crop_box.x = 1
    img.save()
    img.refresh_from_db()
    assert img.crop_box.right == 1
    assert img.crop_box.top == 0
    assert img.crop_box.x == 1
    img.crop_box.x = 5
    with pytest.raises(ValidationError):
        with transaction.atomic():
            img.save()
    img.refresh_from_db()
    # nothing changed
    assert img.crop_box.x == 1