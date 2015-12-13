from rauth import OAuth1Service, OAuth1Session
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import json
import hashlib
import mimetypes
import gi
gi.require_version('GExiv2', '0.10')
from gi.repository import GExiv2

from daguerre.checks import *
from daguerre.logger import *
from daguerre.helpers import *

STATUS_OK = 200
STATUS_RETRY = 429

OAUTH_ORIGIN = 'https://secure.smugmug.com'
REQUEST_TOKEN_URL = OAUTH_ORIGIN + '/services/oauth/1.0a/getRequestToken'
ACCESS_TOKEN_URL = OAUTH_ORIGIN + '/services/oauth/1.0a/getAccessToken'
AUTHORIZE_URL = OAUTH_ORIGIN + '/services/oauth/1.0a/authorize'

UPLOAD_URL = "http://upload.smugmug.com/"
API_ORIGIN = 'https://api.smugmug.com'
MAX_TRIES = 5


def pretty_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))


def add_auth_params(auth_url, access=None, permissions=None):
    if access is None and permissions is None:
        return auth_url
    parts = urlsplit(auth_url)
    query = parse_qsl(parts.query, True)
    if access is not None:
        query.append(('Access', access))
    if permissions is not None:
        query.append(('Permissions', permissions))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, True), parts.fragment))


class PictureToSync(object):
    def __init__(self, filename, md5, uri=None, full_path=None, public=False):
        self.filename = filename
        self.md5 = md5
        self.uri = uri
        self.full_path = full_path
        self.is_public = public

    def __eq__(self, other):
        return (self.filename == other.filename) and (self.md5 == other.md5)

    def __str__(self):
        return "%s %s" % (self.filename, self.md5)


class SyncManager(object):
    def __init__(self, config):
        self.config = config
        pass
        # TODO enter, exit


class SmugMugManager(SyncManager):
    def __init__(self, config):
        super().__init__(config)
        self.api_key = self.config.smugmug["api_key"]
        self.api_key_secret = self.config.smugmug["api_key_secret"]
        self.access_token = ""
        self.access_token_secret = ""
        self.public_tag = self.config.smugmug["public_tag"]
        self.public_node = None
        self.private_node = None
        self.public_albums = []
        self.private_albums = []
        self.known_smugmug_paths = {}
        self.root_node = None
        self.session = None

    def get_tokens(self):
        if "access_token" not in self.config.smugmug:
            service = OAuth1Service(name='pysmug program',
                                    consumer_key=self.api_key,
                                    consumer_secret=self.api_key_secret,
                                    request_token_url=REQUEST_TOKEN_URL,
                                    access_token_url=ACCESS_TOKEN_URL,
                                    authorize_url=AUTHORIZE_URL,
                                    base_url=API_ORIGIN + '/api/v2')
            rt, rts = service.get_request_token(params={'oauth_callback': 'oob'})
            auth_url = add_auth_params(service.get_authorize_url(rt), access='Full', permissions='Modify')
            logger.info('Open web browser to %s.' % auth_url)
            sys.stdout.write('Enter the six-digit code: ')
            sys.stdout.flush()
            verifier = sys.stdin.readline().strip()
            self.access_token, self.access_token_secret = service.get_access_token(rt, rts,
                                                                                   params={'oauth_verifier': verifier})
            # display so that user can copy them in the config file
            logger.info('Add this to your daguerre yaml file, in the smugmug part:')
            logger.info('  access_token: %s' % self.access_token)
            logger.info('  access_token_secret: %s' % self.access_token_secret)
        else:
            # read from file
            self.access_token = self.config.smugmug["access_token"]
            self.access_token_secret = self.config.smugmug["access_token_secret"]

    def _get(self, url, headers={}, params={}, tries=1):
        # TODO filter
        headers['Accept'] = 'application/json'
        params["_verbosity"] = "1"

        get = self.session.get(url,
                               headers=headers,
                               params=params)
        json_answer = json.loads(get.text)
        if json_answer["Code"] == STATUS_OK:
            return True, json_answer["Response"]
        elif json_answer["Code"] == STATUS_RETRY and tries < MAX_TRIES:
            logger.debug("Retrying...")
            time.sleep(1)
            return self._get(url, headers, params, tries=tries + 1)
        else:
            return False, json_answer["Response"]

    def _post(self, url, headers={}, data="", tries=1):
        headers['Accept'] = 'application/json'
        post = self.session.post(url,
                                 data=data,
                                 headers=headers,
                                 header_auth=True)
        json_answer = json.loads(post.text)
        if "Code" in json_answer:
            if json_answer["Code"] == STATUS_OK:
                return True, json_answer["Response"]
            elif json_answer["Code"] == STATUS_RETRY and tries < MAX_TRIES:
                print("Retrying...")
                time.sleep(1)
                return self._post(url, headers, data, tries=tries + 1)
            else:
                return False, json_answer["Response"]
        elif "stat" in json_answer:
            if json_answer["stat"] == "ok":
                return True, json_answer["Image"]
            else:
                return False, json_answer["Image"]

    def _delete(self, uri, headers={}, params={}, tries=1):
        headers['Accept'] = 'application/json'
        params["_verbosity"] = "1"

        delete = self.session.request("DELETE",
                                      uri,
                                      headers=headers,
                                      params=params)
        json_answer = json.loads(delete.text)
        if json_answer["Code"] == STATUS_OK:
            return True, json_answer["Response"]
        elif json_answer["Code"] == STATUS_RETRY and tries < MAX_TRIES:
            logger.debug("Retrying...")
            time.sleep(1)
            return self._delete(uri, headers, params, tries=tries + 1)
        else:
            return False, json_answer["Response"]

    def login(self):
        self.get_tokens()
        self.session = OAuth1Session(self.api_key,
                                     self.api_key_secret,
                                     access_token=self.access_token,
                                     access_token_secret=self.access_token_secret)
        success, response = self._get(API_ORIGIN + '/api/v2!authuser')
        if success:
            user_info = response["User"]
            logger.info("Logged in as %s (%s %s)." % (user_info["Name"],
                                                      user_info["FirstName"],
                                                      user_info["LastName"]))
            logger.info("Domain: %s" % user_info["Domain"])
            logger.info("Image Count: %s" % user_info["ImageCount"])

            self.root_node = user_info["Uris"]["Node"]
        else:
            raise Exception("Could not authenticate user!")

    def _create_album(self, album_name, parent_node, public=False, description=""):
        logger.info("Creating album %s" % album_name)
        data = {
            "Type": "Album",
            "Name": album_name,
            "UrlName": album_name.capitalize(),
            "Description": description,
            "SortMethod": "Name",
            "SortDirection": "Descending",
        }
        if public:
            data["Privacy"] = "Public"
        else:
            data["Privacy"] = "Private"

        headers = {'content-type': 'application/json'}
        success, response = self._post(API_ORIGIN + parent_node + "!children",
                                       headers=headers,
                                       data=json.dumps(data))
        # print(pretty_json(response))
        return success, response

    def create_new_album(self, smugmug_path, public=False, description=""):
        """ Creates a new album. Folders are not created. """
        # split nodes
        nodes = smugmug_path.split("/")
        node_hierarchy = nodes[:-1]
        new_node = nodes[-1]

        # find parent node
        smugmug_node = self.root_node
        smugmug_albumuri = ""
        for node_name in node_hierarchy:
            smugmug_node, smugmug_albumuri = self._find_child_node(smugmug_node, node_name)

        # verify it's a folder
        # TODO do better, it could also be a page
        assert smugmug_node != ""
        assert smugmug_albumuri == ""

        # check it does not exist
        already_exists_node, already_exists_albumuri = self._find_child_node(smugmug_node, new_node)
        try:
            assert already_exists_node == ""
            assert already_exists_albumuri == ""
        except AssertionError:
            logger.warning("Album already exists!")
            if already_exists_albumuri != "":
                self.known_smugmug_paths[smugmug_path] = (already_exists_node,
                                                          already_exists_albumuri)

        # create
        success, response = self._create_album(new_node, smugmug_node, public)
        # adding to known paths
        self.known_smugmug_paths[smugmug_path] = (response["Node"]["Uri"],
                                                  response["Node"]["Uris"]["Album"]["Uri"])
        return success

    def _upload(self, local_path, album_uri):
        """ Upload local picture to an album. """
        with open(local_path.as_posix(), "rb") as f:
            data = f.read()
            headers = {'content-type': mimetypes.guess_type(local_path.name)[0],
                       'X-Smug-ResponseType': 'JSON',
                       'X-Smug-AlbumUri': album_uri,
                       'X-Smug-Version': "v2",
                       'X-Smug-FileName': local_path.name,
                       'Content-MD5': hashlib.md5(data).hexdigest(),
                       'Content-Length': str(len(data))
                       }
            success, response = self._post(UPLOAD_URL,
                                           headers=headers,
                                           data=f)
            return success

    def upload_to_album(self, local_path, smugmug_path):
        if not local_path.exists():
            logger.warning("File %s does not exist." % local_path)
            return False
        smugmug_node, smugmug_albumuri = self._find_leaf_node(smugmug_path)
        return self._upload(local_path, smugmug_albumuri)

    def _upload_to_album_parallel(self, couple):
        local_path, smugmug_path = couple
        return self.upload_to_album(local_path, smugmug_path)

    def _find_child_node(self, root_node, node_name, count=200):
        logger.debug("Trying to find node %s" % node_name)
        parameters = {"_filter": "Name,Uri,Type", "_filteruri": "Album", "count": count, "start": 1}  #
        offset = 1
        total = 10  # not known yet, value not important other than != 0
        while offset != total + 1:
            success, response = self._get(API_ORIGIN + root_node + "!children",
                                          params=parameters)
            # print(pretty_json(response))
            if success and "Node" in response:
                nodes = response["Node"]
                for node in nodes:
                    if node["Name"] == node_name:
                        if node["Type"] == "Album":
                            return node["Uri"], node["Uris"]["Album"]
                        else:
                            return node["Uri"], ""
                if "Pages" in response:
                    parameters["start"] += count
                    offset = response["Pages"]["Count"] + response["Pages"]["Start"]
                    total = response["Pages"]["Total"]
        return "", ""

    def _find_leaf_node(self, smugmug_path):
        if smugmug_path in self.known_smugmug_paths:
            return self.known_smugmug_paths[smugmug_path]
        else:
            # split nodes
            node_hierarchy = smugmug_path.split("/")
            # find the last node's album uri
            smugmug_node = self.root_node
            smugmug_albumuri = ""
            for node_name in node_hierarchy:
                smugmug_node, smugmug_albumuri = self._find_child_node(smugmug_node, node_name)
            assert smugmug_node != ""
            assert smugmug_albumuri != ""
            # adding to known paths
            self.known_smugmug_paths[smugmug_path] = (smugmug_node, smugmug_albumuri)
            return smugmug_node, smugmug_albumuri

    def get_album_images(self, smugmug_path, count=200):
        smugmug_node, smugmug_albumuri = self._find_leaf_node(smugmug_path)
        parameters = {
            # TODO find out why this does not work anymore
            #  "_filter": "ArchivedMD5, FileName, Uri, Format",
            "_filteruri": "Image",
            "count": count,
            "start": 1
        }
        offset = 1
        total = 10  # not known yet, value not important other than != 0
        all_images = []
        while offset != total + 1:
            success, response = self._get(API_ORIGIN + smugmug_albumuri + "!images",
                                          params=parameters)
            if success:
                parameters["start"] += count
                # print(pretty_json(response))
                if "AlbumImage" not in response:
                    break
                all_images.extend(response["AlbumImage"])
                offset = response["Pages"]["Count"] + response["Pages"]["Start"]
                total = response["Pages"]["Total"]

        return all_images

    def _analyze_local_picture(self, path):
        # print(path)
        with open(path.as_posix(), 'rb') as f:
            md5 = hashlib.md5(f.read()).hexdigest()
            exif = GExiv2.Metadata(path.as_posix())
            # read exif tags
            is_public = False
            if exif.has_tag('Iptc.Application2.Keywords'):
                is_public = (self.public_tag in exif.get_tag_multiple('Iptc.Application2.Keywords'))
        return PictureToSync(path.name, md5, full_path=path, public=is_public)

    def get_local_pictures(self, local_path):
        if not local_path.exists():
            logger.warning("%s does not exist." % local_path)
            return []
        else:
            start = time.perf_counter()
            local_pictures = [el for el in local_path.glob('*.jpg')]
            local_pictures.sort()
            all_local_pictures = run_in_parallel(self._analyze_local_picture,
                                                 local_pictures,
                                                 "Analyzing JPG files: ")
            logger.info("JPGs analyzed in %.3fs." % (time.perf_counter() - start))
            return all_local_pictures

    def compare(self, all_local_pictures, smugmug_path, public=True):
        all_pictures = [el for el in all_local_pictures if el.is_public == public]

        start = time.perf_counter()
        all_remote_pictures = []
        images = self.get_album_images(smugmug_path)
        for i in images:
            if i["Format"] == "JPG":
                all_remote_pictures.append(PictureToSync(i["FileName"],
                                                         i["ArchivedMD5"],
                                                         i["Uris"]["Image"]))
        logger.info("Retrieved information from SM in %.3fs." % (time.perf_counter() - start))

        remote_to_delete = [p for p in all_remote_pictures
                            if p not in all_pictures]
        local_to_upload = [p for p in all_pictures
                           if p not in all_remote_pictures]
        # TODO pictures in common between both lists could be replaced

        return local_to_upload, remote_to_delete

    def sync(self, local_path, smugmug_path, public_only=False):
        if not local_path.exists():
            logger.warning("%s does not exist." % local_path)
        else:
            # TODO: only create gallery if necessary (public pictures this month)

            all_local_pictures = self.get_local_pictures(local_path)

            public_path = "%s/%s" % (self.config.smugmug["public_folder"],
                                     smugmug_path)
            logger.info("Syncing public pictures from %s with %s" % (local_path, public_path))

            # check if gallery exists, else create it
            try:
                self._find_leaf_node(public_path)
            except AssertionError:
                self.create_new_album(public_path, public=True)

            upload_local, delete_remote = self.compare(all_local_pictures,
                                                       public_path,
                                                       public=True)

            start = time.perf_counter()
            source_list = [API_ORIGIN + d.uri for d in delete_remote]
            run_in_parallel(self._delete,
                            source_list,
                            "Deleting files: ")
            logger.info("Deleted pictures from public SM in %.3fs." % (time.perf_counter() - start))

            start = time.perf_counter()
            source_list = [(u.full_path, public_path) for u in upload_local]
            run_in_parallel(self._upload_to_album_parallel,
                            source_list,
                            "Uploading files: ")
            logger.info("Uploaded pictures to public SM in %.3fs." % (time.perf_counter() - start))

            if not public_only:
                private_path = "%s/%s" % (self.config.smugmug["private_folder"],
                                          smugmug_path)
                logger.info("Syncing private pictures from %s with %s" % (local_path, private_path))
                # check if gallery exists, else create it
                try:
                    self._find_leaf_node(private_path)
                except AssertionError:
                    self.create_new_album(private_path, public=False)

                upload_local, delete_remote = self.compare(all_local_pictures,
                                                           private_path,
                                                           public=False)

                start = time.perf_counter()
                source_list = [API_ORIGIN + d.uri for d in delete_remote]
                run_in_parallel(self._delete,
                                source_list,
                                "Deleting files: ")
                logger.info("Deleted pictures from private SM in %.3fs." % (time.perf_counter() - start))

                start = time.perf_counter()
                source_list = [(u.full_path, private_path) for u in upload_local]
                run_in_parallel(self._upload_to_album_parallel,
                                source_list,
                                "Uploading files: ")
                logger.info("Uploaded pictures to private SM in %.3fs." % (time.perf_counter() - start))
