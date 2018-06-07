"""
This XBlock lets you upload content packaged into SCORM files and display it to students.
Additionally it provides an API access to the original SCORM file with
additional metadata like last_updated date/time.
"""

import logging
import os
import pkg_resources
import shutil
import tempfile

from zipfile import ZipFile

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.utils import timezone
from storages.backends.s3boto import S3BotoStorage
from webob import Response

from xblock.core import XBlock
from xblock.fields import Scope, Dict, String
from xblock.fragment import Fragment

from .utils import get_sha1, make_file_response


# Make '_' a no-op so we can scrape strings
_ = lambda text: text

log = logging.getLogger(__name__)

SCORM_ROOT = os.path.join(settings.ENV_TOKENS['MEDIA_ROOT'], 'scorm')
FOLDERS_BLACKLIST = ('.DS_Store', '__MACOSX')

# TODO: Cleanup files from the storage on Xblock delete


class ScormXBlock(XBlock):
    """
    On scorm file upload this xblock stores it into default_storage,
    which can be either filesystem based or S3.
    Then it unpacks scorm file contents into MEDIA_ROOT/scorm subdirectory
    to serve it to students.
    """

    display_name = String(
        display_name=_("Display Name"),
        help=_("Display name for this module"),
        default="Scorm",
        scope=Scope.settings,
    )
    scorm_file = String(
        display_name=_("Upload scorm file"),
        scope=Scope.settings,
    )
    scorm_file_meta = Dict(
        scope=Scope.content)

    icon_class = 'video'

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def studio_view(self, context=None):
        html = self.resource_string("static/html/studio.html")
        frag = Fragment(html.format(self=self))
        frag.add_javascript(self.resource_string("static/js/src/studio.js"))
        frag.initialize_js('ScormStudioXBlock')
        return frag

    def student_view(self, context=None):
        """
        The primary view of the ScormXBlock, shown to students
        when viewing courses.
        """
        html = self.resource_string("static/html/scorm.html")
        story_base_url = self.scorm_file_meta.get('story_base_url')
        start_html_file = 'index.html'
        if story_base_url:
            frag = Fragment(html.format(
                story_base_url=story_base_url,
                start_html_file=start_html_file,
					 tincan=True,
					 endpoint='http://localhost:88/api/',
					 auth='Basic MmVjZTZkMzZiMDkxNTdmNTNmMDhiMTA5ZmEyNDNmMWE4Y2NiNGNjMjoxMWVkZGRlMTk1YjQ2OGNiZWEzYjU3NGQyNThiYmI4NGUxMjI0YmIz'
					 actor='{"name": ["Harsheen chauhan"], "mbox": ["mailto:Harsheen@flipick.com"], "objectType": ["Agent"]}',
					 registration='2981c910-6445-11e4-9803-0800200c9a66'
            ))
        else:
            frag = Fragment()
        frag.add_javascript(self.resource_string("static/js/src/scorm.js"))
        frag.initialize_js('ScormXBlock')
        return frag

    def student_view_data(self):
        """
        Inform REST api clients about original file location and it's "freshness".
        Make sure to include `student_view_data=scorm` to URL params in the request.
        """
        return {'last_modified': self.scorm_file_meta['last_updated'],
                'scorm_data': self._get_file_url()}

    def _get_file_url(self):
        if isinstance(default_storage, S3BotoStorage):
            return default_storage.url(self._file_storage_path())
        return self.runtime.handler_url(self, 'scorm_data_file', thirdparty=True)

    @XBlock.handler
    def studio_submit(self, request, suffix=''):
        self.display_name = request.params['display_name']
        if not hasattr(request.params['file'], 'file'):
            return Response(json_body={'result': 'success'})

        scorm_file = request.params['file'].file

        # First, save scorm file in the storage for mobile clients
        self.scorm_file_meta['sha1'] = get_sha1(scorm_file)
        self.scorm_file_meta['name'] = scorm_file.name
        self.scorm_file_meta['path'] = path = self._file_storage_path()
        self.scorm_file_meta['last_updated'] = timezone.now()

        if default_storage.exists(path):
            log.info('Removing previously uploaded "{}"'.format(path))
            default_storage.delete(path)

        default_storage.save(path, File(scorm_file))
        log.info('"{}" file stored at "{}"'.format(scorm_file, path))

        # Now unpack it into SCORM_ROOT to serve to students later
        with ZipFile(scorm_file, 'r') as zip_file:
            temp_dir = tempfile.mkdtemp()
            target_path = os.path.join(SCORM_ROOT, self.location.block_id)
            if os.path.exists(target_path):
                log.info('Removing previously unpacked contents at "{}"'.format(target_path))
                shutil.rmtree(target_path)

            zip_file.extractall(temp_dir)
            content_dir = [d for d in os.listdir(temp_dir) if d not in FOLDERS_BLACKLIST]
            log.info('Moving scorm file contents into {}'.format(target_path))
            shutil.move(os.path.join(temp_dir, content_dir[0]), target_path)

            shutil.rmtree(temp_dir)

        scorm_base_url = '//{}/{}/scorm'.format(
            settings.LMS_BASE, settings.ENV_TOKENS['MEDIA_URL'].strip('/'))
        self.scorm_file_meta['story_base_url'] = '{}/{}'.format(
            scorm_base_url, self.location.block_id
        )
        self.scorm_file = os.path.join(
            SCORM_ROOT, self.location.block_id, 'story.html'
        )

        return Response(json_body={'result': 'success'})

    @XBlock.handler
    def scorm_data_file(self, request, suffix=''):
        file_name = self._file_storage_path()
        return make_file_response(default_storage, file_name)

    def _file_storage_path(self):
        """
        Get file path of storage.
        """
        path = (
            '{loc.org}/{loc.course}/{loc.block_type}/{loc.block_id}'
            '/{sha1}{ext}'.format(
                loc=self.location,
                sha1=self.scorm_file_meta['sha1'],
                ext=os.path.splitext(self.scorm_file_meta['name'])[1]
            )
        )
        return path
