# edx_scorm_xblock

## Installation

Install this package into virtualenv open edx uses
```shell
ubuntu@theteacherapp:~$ git clone git@github.com:TeacherAppFoundation/edx_scorm_xblock.git
ubuntu@theteacherapp:~$ cd edx_scorm_xblock
ubuntu@theteacherapp:~$ sudo -u edxapp /edx/bin/pip.edxapp install .
```
Enable advanced components in `/edx/app/edx_ansible/server-vars.yml`
```yaml
EDXAPP_FEATURES:
    ALLOW_ALL_ADVANCED_COMPONENTS: true
```
Add "scorm" in the course's _Advanced Module List_ in Advanced Settings in the Studio.

## Configuration
This xblock needs S3 storage configured to store original scorm files for data sync with the mobile app.

S3 storage is recomended.

### S3 file storage
To configure S3 storage properly one need to set following options in the `server-vars.yml`:

```yaml
EDXAPP_AWS_ACCESS_KEY_ID: 'your access key id'
EDXAPP_AWS_SECRET_ACCESS_KEY: 'your secret access key'
EDXAPP_AWS_S3_CUSTOM_DOMAIN: "example.s3.amazonaws.com"
EDXAPP_AWS_STORAGE_BUCKET_NAME: "bucket name"
```

Make sure you have following line in `edx-platform/cms/envs/aws.py`
```python
AWS_STORAGE_BUCKET_NAME = AUTH_TOKENS.get('AWS_STORAGE_BUCKET_NAME', 'edxuploads')
```

*Note:* Currently boto python package does not support newest AWS location Mumbai. This means you need to create a S3 bucket in another location to make it work with this xblock.
