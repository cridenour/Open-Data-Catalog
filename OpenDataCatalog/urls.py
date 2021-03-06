from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.contrib.sitemaps import FlatPageSitemap, GenericSitemap
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


from OpenDataCatalog.opendata.feeds import ResourcesFeed, TagFeed, IdeasFeed, UpdatesFeed
from OpenDataCatalog.opendata.models import Resource, Idea
from OpenDataCatalog.registration_backend import CatalogRegistrationView

from OpenDataCatalog.opendata.views import ResourceView, UserView, SubmitDataView, HomeView, ResultsView, \
    TagResultsView, SearchResultsView, IdeaResultsView, IdeaDetailView, TagListView, FeedListView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

sitemaps = {
    'flatpages': FlatPageSitemap,
    'resources': GenericSitemap({'queryset': Resource.objects.all(), 'date_field': 'created'}, priority=0.5),
    'ideas': GenericSitemap({'queryset': Idea.objects.all(), 'date_field': 'created_by_date'}, priority=0.5),
}

urlpatterns = patterns('',
    url(r'^$', HomeView.as_view(), name='home'),

    # The API urls
    url(r'^api/', include('OpenDataCatalog.api.urls')),
    url(r'^comments/', include('django.contrib.comments.urls')),
    url(r'^catalog/', include("OpenDataCatalog.catalog.urls")),
    url(r'^accounts/', include('registration.backends.default.urls')),
    url(r'^contest/', include('OpenDataCatalog.contest.urls')),
    url(r'^opendata/nominate/', include('OpenDataCatalog.suggestions.urls'), name='nominate'),
    url(r'^visualization/', include('OpenDataCatalog.visualization.urls')),

    url(r'^opendata/$', ResultsView.as_view(), name='results'),

    url(r'^opendata/tag/(?P<tag_id>\d+)/$', TagResultsView.as_view(), name='tag'),
    url(r'^opendata/search/$', SearchResultsView.as_view(), name='search'),
    url(r'^opendata/resource/(?P<resource_id>\d+)/$', ResourceView.as_view()),
    url(r'^opendata/resource/(?P<resource_id>\d+)/(?P<slug>[-\w]+)/$', ResourceView.as_view()),
    url(r'^opendata/submit/$', SubmitDataView.as_view(), name='submit'),
    url(r'^opendata/submit/thanks/$', TemplateView.as_view(template_name='thanks.html'), name='submit-thanks'),
    url(r'^ideas/$', IdeaResultsView.as_view(), name='ideas'),
    url(r'^idea/(?P<idea_id>\d+)/$', IdeaDetailView.as_view(), name='idea'),
    url(r'^idea/(?P<idea_id>\d+)/(?P<slug>[-\w]+)/$', IdeaDetailView.as_view(), name='idea-slug'),
    url(r'^thanks/$', TemplateView.as_view(template_name='thanks.html'), name='thanks'),
    
    url(r'^tags/$', TagListView.as_view(), name='tag-list'),

    url(r'^feeds/$', FeedListView.as_view(), name='feed-list'),
    url(r'^feeds/resources/$', ResourcesFeed(), name='resources-feed'),
    url(r'^feeds/updates/$', UpdatesFeed(), name='updates-feed'),
    url(r'^feeds/ideas/$', IdeasFeed(), name='ideas-feed'),
    url(r'^feeds/tag/(?P<tag_id>\d+)/$', TagFeed(), name='tag-feed'),

    # User specific
    url(r'^users/(?P<username>\w+)/', UserView.as_view(), name='user'),
    url(r'^accounts/register/$', CatalogRegistrationView.as_view(), name='registration_register'),
    url(r'^accounts/password_reset/', 'django.contrib.auth.views.password_reset'),

    # Uncomment the next line to enable the admin:
    url(r'^_admin_/', include(admin.site.urls)),

    url(r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
    url(r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt')),


) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Process static files properly
urlpatterns += staticfiles_urlpatterns()

# Catch all for static pages
#urlpatterns += patterns('django.contrib.flatpages.views',
#    (r'^(?P<url>.*/)$', 'flatpage'),
#)
