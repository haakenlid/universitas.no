# Generated by Django 2.1 on 2018-10-22 22:21

from django.db import migrations
import utils.model_fields


class Migration(migrations.Migration):

    dependencies = [
        ('photo', '0028_auto_20180831_2338'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imagefile',
            name='crop_box',
            field=utils.model_fields.CropBoxField(
                help_text='How this image has been cropped.',
                null=True,
                verbose_name='crop box'
            ),
        ),
    ]
