#!/usr/bin/env python3
# Copyright (C) 2012-2013, The CyanogenMod Project
#           (C) 2017-2018,2020-2021, The LineageOS Project
#           (C) 2026, The haloUI Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import base64
import glob
import json
import netrc
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

from xml.etree import ElementTree

dryrun = os.getenv('ROOMSERVICE_DRYRUN') == 'true'
if dryrun:
    print('Dry run roomservice, no change will be made.')

product = sys.argv[1]

if len(sys.argv) > 2:
    depsonly = sys.argv[2]
else:
    depsonly = None

try:
    device = product[product.index('_') + 1:]
except ValueError:
    device = product

if not depsonly:
    print(f'Device {device} not found. Searching GitHub and Codeberg...')

repositories = []

try:
    authtuple = netrc.netrc().authenticators('api.github.com')
    if authtuple:
        auth_string = ('%s:%s' % (authtuple[0], authtuple[2])).encode()
        githubauth = base64.b64encode(auth_string).decode()
    else:
        githubauth = None
except Exception:
    githubauth = None

def add_auth(req):
    if githubauth and 'github.com' in req.full_url:
        req.add_header('Authorization', 'Basic %s' % githubauth)

def fetch_repos():
    device_q = urllib.parse.quote(device)

    def search_github_org(org, remote_name):
        gh_url = ('https://api.github.com/search/repositories?q=%s+user:%s+in:name+fork:true'
                  % (device_q, urllib.parse.quote(org)))
        gh_req = urllib.request.Request(gh_url)
        add_auth(gh_req)
        try:
            gh_res = json.loads(urllib.request.urlopen(gh_req, timeout=10).read().decode())
            for item in gh_res.get('items', []):
                item['found_on'] = remote_name
                repositories.append(item)
        except Exception:
            print(f'GitHub search failed for org {org}')

    search_github_org('HaloUI-Devices', 'haloui-devices')
    search_github_org('HaloUI-AOSP', 'haloui')

    cb_url = 'https://codeberg.org/api/v1/repos/search?q=%s&owner=zenin1504' % device_q
    cb_req = urllib.request.Request(cb_url)
    try:
        cb_res = json.loads(urllib.request.urlopen(cb_req, timeout=10).read().decode())
        items = cb_res.get('data', cb_res) if isinstance(cb_res, dict) else cb_res
        for item in items:
            item['found_on'] = 'codeberg'
            repositories.append(item)
    except Exception:
        print('Codeberg search failed')

if not depsonly:
    fetch_repos()

local_manifests = r'.repo/local_manifests'
if not os.path.exists(local_manifests):
    os.makedirs(local_manifests)

def indent(elem, level=0):
    i = '\n' + level * '  '
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + '  '
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent(child, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def get_manifest_path():
    m = ElementTree.parse('.repo/manifest.xml')
    try:
        m.findall('default')[0]
        return '.repo/manifest.xml'
    except IndexError:
        return f'.repo/manifests/{m.find("include").get("name")}'

def get_from_manifest(devicename):
    device_re = re.escape(devicename)
    for path in glob.glob('.repo/local_manifests/*.xml'):
        try:
            lm = ElementTree.parse(path).getroot()
            for lp in lm.findall('project'):
                if re.search(f'{device_re}$', lp.get('path', '')):
                    return lp.get('path')
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f'Warning: could not parse {path}: {e}')
    return None

def get_roomservice_paths():
    paths = set()
    rs = '.repo/local_manifests/roomservice.xml'
    if not os.path.exists(rs):
        return paths
    try:
        lm = ElementTree.parse(rs).getroot()
        for p in lm.findall('project'):
            path = p.get('path')
            if path:
                paths.add(path)
    except Exception as e:
        print(f'Warning: could not parse {rs}: {e}')
    return paths

def is_in_roomservice(path):
    return path in get_roomservice_paths()

def add_to_manifest(dependencies):
    if dryrun:
        for dep in dependencies:
            print(f"[dry run] would add project {dep['repository']} -> {dep['target_path']} "
                  f"(remote={dep.get('remote', 'haloui-devices')})")
        return
    try:
        lm = ElementTree.parse('.repo/local_manifests/roomservice.xml').getroot()
    except Exception:
        lm = ElementTree.Element('manifest')

    existing = set()
    for p in lm.findall('project'):
        if p.get('path'):
            existing.add(p.get('path'))

    for dep in dependencies:
        if dep.get('type') != 'project':
            continue
        if dep['target_path'] in existing:
            continue
        p = ElementTree.Element('project', attrib={
            'path': dep['target_path'],
            'remote': dep.get('remote', 'haloui-devices'),
            'name': dep['repository']
        })
        if dep.get('branch'):
            p.set('revision', dep['branch'])
        lm.append(p)
        existing.add(dep['target_path'])

    indent(lm, 0)
    with open('.repo/local_manifests/roomservice.xml', 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + ElementTree.tostring(lm).decode())

def get_default_revision(remote_name):
    try:
        lm = ElementTree.parse('.repo/manifests/snippets/haloui.xml').getroot()
        node = lm.find(f".//remote[@name='{remote_name}']")
        if node is None:
            return "main"
        rev = node.get('revision')
        if not rev:
            return "main"
        return rev.split('/')[-1]
    except Exception:
        return "main"

def repo_sync(paths):
    if dryrun:
        print(f"[dry run] would run: repo sync --force-sync {' '.join(paths)}")
        return True
    result = subprocess.run(['repo', 'sync', '--force-sync'] + paths)
    if result.returncode != 0:
        print(f"Error: repo sync failed for {' '.join(paths)} (exit {result.returncode})")
        return False
    return True

def is_synced(path):
    return os.path.isdir(path) and any(os.scandir(path))

def fetch_dependencies(repo_path, depth=0):
    if depth > 10:
        print(f'Warning: dependency recursion limit hit at {repo_path}')
        return
    dep_file = os.path.join(repo_path, 'haloui.dependencies')
    if not os.path.exists(dep_file):
        return
    with open(dep_file, 'r') as f:
        dependencies = json.load(f)

    deps = []
    for dep in dependencies:
        dep['repository'] = dep.get('repository', dep.get('name'))
        dep['type'] = 'project'
        if 'remote' not in dep:
            dep['remote'] = 'haloui-devices'
        if not dep['repository'] or not dep.get('target_path'):
            print(f"Warning: skipping malformed dependency {dep}")
            continue
        if not dep.get('branch'):
            dep['branch'] = get_default_revision(dep['remote'])
        deps.append(dep)

    to_add = [d for d in deps if not is_in_roomservice(d['target_path'])]
    if to_add:
        add_to_manifest(to_add)

    sync_list = [d for d in deps if not is_synced(d['target_path'])]

    if not sync_list:
        return

    synced_paths = []
    failed_paths = []
    for dep in sync_list:
        path = dep['target_path']
        if not is_in_roomservice(path):
            print(f"Warning: {path} still missing from roomservice.xml, skipping")
            failed_paths.append(path)
            continue
        if repo_sync([path]):
            synced_paths.append(path)
        else:
            failed_paths.append(path)

    if failed_paths:
        print(f"Warning: {len(failed_paths)} dependenc{'y' if len(failed_paths) == 1 else 'ies'} "
              f"failed to sync and were skipped: {', '.join(failed_paths)}")

    for path in synced_paths:
        fetch_dependencies(path, depth + 1)

if depsonly:
    path = get_from_manifest(device)
    if path:
        fetch_dependencies(path)
    else:
        print(f'Device {device} not found in local manifests.')
        sys.exit(1)
    sys.exit()

found = False
for repo in repositories:
    name = repo['name']
    match = re.search(
        r'(?:^|_)(?:android_)?(device|vendor|kernel|hardware)_(.+)_' + re.escape(device) + r'$'
        r'|^android_(hardware|vendor)_qcom_(.+)$',
        name
    )

    if match:
        if match.group(1):
            repo_type = match.group(1)
            manufacturer = match.group(2)
            target_path = f'{repo_type}/{manufacturer}/{device}'
        else:
            repo_type = match.group(3)
            qcom_name = match.group(4)
            target_path = f'{repo_type}/qcom/{qcom_name}'
        remote = repo.get('found_on', 'haloui-devices')

        print(f'Found: {name} on {remote} -> {target_path}')
        add_to_manifest([{
            'repository': name,
            'target_path': target_path,
            'branch': get_default_revision(remote),
            'remote': remote,
            'type': 'project'
        }])

        if repo_sync([target_path]):
            fetch_dependencies(target_path)
            found = True
            break
        else:
            print(f'Warning: failed to sync {target_path}, trying next match')
            found = True
            continue

if not found:
    print(f'Repository for {device} not found.')
    sys.exit(1)

sys.exit(0)
