from django.db import models

from geopy import geocoders
from geopy.geocoders.googlev3 import GQueryError, GTooManyQueriesError

from streetaddress import StreetAddressParser

from urllib2 import HTTPError


class CincinnatiPolice(models.Model):
    event_number = models.CharField(max_length=50, help_text=u'Event #')
    create_date = models.DateField(null=True)
    address = models.CharField(max_length=30, blank=True, default='')
    anon_address = models.CharField(max_length=50, blank=True, default='')
    description = models.CharField(max_length=50)
    location = models.CharField(max_length=50, blank=True, default='')

    latitude = models.FloatField(null=True, default=0.0)
    longitude = models.FloatField(null=True, default=0.0)

    def __unicode__(self):
        return u'%s' % self.description

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.address = self.address.strip()
        self.description = self.description.strip()
        self.location = self.location.strip()

        if self.address and not self.anon_address:
            # Let's anonymize this address
            address = StreetAddressParser().parse(self.address)

            if address.get('block') and int(address.get('block')) > 0:
                self.anon_address = u'%s block of %s' % (address.get('block'), address.get('street_full'))
            else:
                self.anon_address = self.address

        return super(CincinnatiPolice, self).save(force_insert, force_update, using, update_fields)


class Arrest(models.Model):
    arrest_type = models.IntegerField(default=0, null=True)
    control_number = models.IntegerField(default=0, null=True)
    rac = models.CharField(max_length=10, blank=True, default='')  # TODO: Determine meaning
    sex = models.CharField(max_length=1, default='', blank=True)
    ra = models.IntegerField(default=0, null=True)  # TODO: Determine meaning
    event_date = models.DateField()
    event_time = models.TimeField()
    secno = models.CharField(max_length=20, blank=True, default='')
    seccode = models.CharField(max_length=20, blank=True, default='')
    dob_year = models.IntegerField(null=True, blank=True)
    charge_code = models.IntegerField(null=True, blank=True)
    charge_type = models.IntegerField(null=True, blank=True)
    arrest_disp_code = models.IntegerField(null=True, blank=True)
    badge_number = models.IntegerField(null=True, blank=True)
    officer = models.CharField(max_length=30, blank=True, default='')
    nature = models.IntegerField(null=True, blank=True)
    report_number = models.CharField(max_length=30, default='', blank=True)

    # These will be anonymized into new fields
    arrest_address = models.CharField(max_length=50, default='', blank=True)
    home_address = models.CharField(max_length=50, default='', blank=True)
    home_city = models.CharField(max_length=50, default=u'Cincinnati', blank=True)
    home_state = models.CharField(max_length=2, default=u'OH', blank=True)
    home_zip = models.IntegerField(null=True)

    anon_arrest_address = models.CharField(max_length=50, default='', blank=True)
    anon_home_address = models.CharField(max_length=50, default='', blank=True)

    def __unicode__(self):
        return u'Arrest at %s' % self.anon_arrest_address

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.arrest_address = self.arrest_address.strip()
        self.home_address = self.home_address.strip()

        if self.arrest_address and not self.anon_arrest_address:
            address = StreetAddressParser().parse(self.arrest_address)

            if address.get('block') and int(address.get('block')) > 0:
                self.anon_arrest_address = u'%s block of %s' % (address.get('block'), address.get('street_full'))
            else:
                self.anon_arrest_address = self.arrest_address

        if self.home_address and not self.anon_home_address:
            address = StreetAddressParser().parse(self.home_address)

            if address.get('block') and int(address.get('block')) > 0:
                self.anon_home_address = u'%s block of %s' % (address.get('block'), address.get('street_full'))
            else:
                self.anon_home_address = self.arrest_address

        return super(Arrest, self).save(force_insert, force_update, using, update_fields=update_fields)


class ThreeOneOne(models.Model):
    csr = models.CharField(max_length=15, help_text=u'CSR #')
    status = models.CharField(max_length=20, help_text=u'Status of the call')
    request_type = models.CharField(max_length=100)
    description = models.TextField(blank=True, default=u'')
    date_received = models.DateTimeField(null=True)
    street_address = models.CharField(max_length=100, blank=True)
    community = models.CharField(max_length=100, blank=True)
    census_tract = models.FloatField(null=True, blank=True)
    priority = models.CharField(max_length=20, blank=True)
    method = models.CharField(max_length=50, blank=True)
    parcel_number = models.CharField(max_length=30, blank=True, help_text=u'Land parcel number')
    date_answered = models.DateField()
    user_id = models.CharField(max_length=20)
    planned_completion_date = models.DateField(null=True)
    revised_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True)
    status_date = models.DateField(null=True)
    assignee_id = models.CharField(max_length=20, blank=True,)

    latitude = models.FloatField(null=True, default=0.0)
    longitude = models.FloatField(null=True, default=0.0)

    class Meta:
        verbose_name = u'311 report'
        verbose_name_plural = u'311 reports'

    def __unicode__(self):

        return unicode(self.request_type)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):

        if self.latitude == 0 and self.longitude == 0:

            address = '%s Cincinnati, OH' % self.street_address

            google = geocoders.GoogleV3()

            try:
                place, (lat, lon) = google.geocode(address, exactly_one=False)[0]
            except GQueryError:
                lat = 0
                lon = 0
            except GTooManyQueriesError:
                lat = 0
                lon = 0
            except HTTPError, e:
                lat = 0
                lon = 0

            self.latitude = lat
            self.longitude = lon

        return super(ThreeOneOne, self).save(force_insert, force_update, using, update_fields)
