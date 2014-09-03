# -*- coding: utf-8 -*-
"""
Admin for frontpage app.
"""

from django.contrib import admin
from .models import Contentblock, FrontpageStory
import autocomplete_light

class ContentblockInline(admin.TabularInline):
    # form = autocomplete_light.modelform_factory(FrontpageStory)
    model = Contentblock
    fields = ( 'position', 'columns', 'height',),
    extra = 0

@admin.register(FrontpageStory)
class FrontpageStoryAdmin(admin.ModelAdmin):
    form = autocomplete_light.modelform_factory(FrontpageStory)
    save_on_top = True
    list_per_page = 25
    list_display = (
        'id',
        'kicker',
        'headline',
        'lede',
        'image',
        'story',
        'horizontal_centre',
        'vertical_centre',
        # 'placements',
    )

    list_editable = (
        'headline',
        # 'kicker',
        # 'lede',
        'horizontal_centre',
        'vertical_centre',
    )
    inlines = (
        ContentblockInline,
    )
    search_fields = (
        'headline',
        'kicker',
    )

@admin.register(Contentblock)
class ContentblockAdmin(admin.ModelAdmin):

    save_on_top = True
    list_per_page = 25
    list_display = (
        'id',
        'frontpage_story',
        'publication_date',
        'position',
        'columns',
        'height',
        'frontpage',
    )

    list_editable = (
        'position',
        'columns',
        'height',
    )
    # inlines = (
    #     FrontpageStoryInline,
    # )