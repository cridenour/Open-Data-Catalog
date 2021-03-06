from datetime import datetime
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.core import serializers
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, FormView, View
from django.utils.decorators import method_decorator
from django.core.cache import cache

from pytz import timezone
from pytz import utc

from models import TwitterCache
import twitter
import simplejson as json
import random

from OpenDataCatalog.opendata.models import *
from OpenDataCatalog.opendata.forms import *
from OpenDataCatalog.contest.models import Vote
from OpenDataCatalog.suggestions.models import Suggestion
from .utils import send_email
from datetime import date


class ResourceView(TemplateView):
    template_name = 'details.html'

    def dispatch(self, request, *args, **kwargs):
        # Get the resource
        resource = get_object_or_404(Resource, pk=kwargs.get('resource_id'))

        kwargs['resource'] = resource

        return super(ResourceView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        return {
            'resource': kwargs.get('resource'),
        }


class UserView(TemplateView):
    template_name = 'users/user.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        # Verify that the user can see this profile
        if not request.user.is_superuser:
            return redirect('home')

        return super(UserView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Pull information back about the user.
        - Profile
        - Resources
        - Nominations
        - Votes
        - Ideas
        """
        the_user = User.objects.get(username=kwargs.get('username'))
        return {
            'the_user': the_user,
            'resources': Resource.objects.filter(created_by=the_user).order_by('name'),
            'submissions': Submission.objects.filter(user=the_user).order_by('-sent_date'),
            'votes': Vote.objects.filter(user=the_user),
        }


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        tweets = cache.get('tweets')

        local = timezone('US/Eastern')

        if not tweets and settings.TWITTER_USER:
            tweets = twitter.Api().GetUserTimeline(settings.TWITTER_USER)[:4]
            if tweets.count < 4:
                tweet_cache = []
                for t in TwitterCache.objects.all():
                    tc = json.JSONDecoder().decode(t.text)
                    tc['date'] = datetime.strptime(tc['created_at'], "%a %b %d %H:%M:%S +0000 %Y")\
                        .replace(tzinfo=utc).astimezone(local)
                    tweet_cache.append(tc)
                tweets = tweet_cache
            else:
                TwitterCache.objects.all().delete()

                for tweet in tweets:
                    tweet.date = datetime.strptime(tweet.created_at, "%a %b %d %H:%M:%S +0000 %Y")\
                        .replace(tzinfo=utc).astimezone(local)

                    t = TwitterCache(text=tweet.AsJsonString())
                    t.save()

                cache.set('tweets', tweets, settings.TWITTER_TIMEOUT)

        # Cache these for three minutes
        recent = cache.get('recent_resources')
        if not recent:
            recent = Resource.objects.order_by("-created")[:3]
            cache.set('recent_resources', recent, 180)

        if Idea.objects.count() > 0:
            ideas = Idea.objects.order_by("-created_by_date")[:4]
            idea = ideas[random.randint(0, ideas.count() - 1)]
        else:
            idea = None

        return {
            'recent': recent,
            'idea': idea,
            'tweets': tweets
        }


class ResultsView(TemplateView):
    template_name = 'results.html'

    def get_context_data(self, **kwargs):
        resources = Resource.objects.all()

        if 'filter' in self.request.GET:
            f = self.request.GET.get('filter')
            resources = resources.filter(resource_urls__url_type__url_type__iexact=f).distinct()

        return {
            'results': resources
        }


class TagResultsView(TemplateView):
    template_name = 'results.html'

    def get_context_data(self, **kwargs):
        tag = Tag.objects.get(pk=kwargs.get('tag_id'))
        tag_resources = Resource.objects.filter(tags=tag, is_published=True)

        if 'filter' in self.request.GET:
            f = self.request.GET['filter']
            tag_resources = tag_resources.filter(url__url_type__url_type__icontains=f).distinct()

        return {
            'results': tag_resources,
            'tag': tag,
        }


class SearchResultsView(TemplateView):
    template_name = 'results.html'

    def get_context_data(self, **kwargs):
        search_resources = Resource.objects.all()

        if 'qs' in self.request.GET:
            qs = self.request.GET.get('qs', '').replace("+", " ")
            search_resources = Resource.search(qs, search_resources)

        if 'filter' in self.request.GET:
            f = self.request.GET.get('filter')
            search_resources = search_resources.filter(url__url_type__url_type__iexact=f).distinct()

        return {
            'results': search_resources,
        }


class IdeaResultsView(TemplateView):
    template_name = 'ideas.html'

    def get_context_data(self, **kwargs):

        ideas = Idea.objects.order_by("-created_by_date")
        return {
            'ideas': ideas
        }


class IdeaDetailView(TemplateView):
    template_name = 'idea_details.html'

    def get_context_data(self, **kwargs):
        # If we have a specific idea, we are going to show a certain view.
        idea = get_object_or_404(Idea, pk=kwargs.get('idea_id'))

        return {
            'idea': idea
        }


class FeedListView(View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        """
        Return the list of feeds
        """
        tags = Tag.objects.all()
        return render_to_response('feeds/list.html', context_instance=RequestContext(request, {'tags': tags}))


class SubmitDataView(FormView):
    template_name = 'submit.html'
    success_url = '/opendata/submit/thanks/'
    form_class = SubmissionForm

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        return super(SubmitDataView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        coords, types, formats, updates = "", "", "", ""
        for c in self.request.POST.getlist("coord_system"):
            coords = coords + " EPSG:" + CoordSystem.objects.get(pk=c).EPSG_code.__str__()
        for t in self.request.POST.getlist("types"):
            types = types + " " + UrlType.objects.get(pk=t).url_type
        for f in self.request.POST.getlist("formats"):
            formats = formats + " " + DataType.objects.get(pk=f).data_type
        for u in self.request.POST.getlist("update_frequency"):
            if u:
                updates = updates + " " + UpdateFrequency.objects.get(pk=u).update_frequency

        data = {
            "submitter": self.request.user.username,
            "submit_date": datetime.now(),
            "dataset_name": form.cleaned_data.get("dataset_name"),
            "description": form.cleaned_data.get('description'),
            "organization": form.cleaned_data.get("organization"),
            "copyright_holder": form.cleaned_data.get("copyright_holder"),
            "contact_email": form.cleaned_data.get("contact_email"),
            "contact_phone": form.cleaned_data.get("contact_phone"),
            "url": form.cleaned_data.get("url"),
            "time_period": form.cleaned_data.get("time_period"),
            "release_date": form.cleaned_data.get("release_date"),
            "area_of_interest": form.cleaned_data.get("area_of_interest"),
            "update_frequency": updates,
            "coord_system": coords,
            "wkt_geometry": form.cleaned_data.get("wkt_geometry"),
            "types": types,
            "formats": formats,
            "usage_limitations": form.cleaned_data.get("usage_limitations"),
            "collection_process": form.cleaned_data.get("collection_process"),
            "data_purpose": form.cleaned_data.get("data_purpose"),
            "intended_audience": form.cleaned_data.get("intended_audience"),
            "why": form.cleaned_data.get("why"),
        }

        # A Submission() is created in this method.  This is not ideal.
        send_email(self.request.user, data)

        # Create a nomination (Suggestion)
        s = Suggestion()
        s.text = data.get('dataset_name')[:255]
        s.description = data.get('description') if data.get('description') else ''
        s.suggested_by = self.request.user
        # suggestion.suggested_date = submission.sent_date
        s.last_modified_date = date.today()
        s.save()

        return super(SubmitDataView, self).form_valid(form)


class TagListView(View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        """
        Gets the tags and serializes them for ajax requests
        """
        tags = Tag.objects.all()
        return HttpResponse(serializers.serialize("json", tags), content_type='application/json')

