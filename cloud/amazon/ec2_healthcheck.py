#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
module: ec2_healthcheck
short_description: Waits for an ec2 instance to become reachable.
description:
     - Performs a health check to an ec2 instance by checking its' status
       several times in a given interval, until the instance becomes reachable.
       The module assumes the instance already exists.
requirements:
    - "boto"
options:
  instance_id:
    description:
      - The ID of the ec2 instance.
    required: true
  region:
    description:
      - The ec2 region.
    required: true
  interval:
    description:
      - The time interval (in seconds) between each health check.
    required: true
  repeat:
    description:
      - The number of times to perform an aditional health check after the
        previous one (0 = only one check will be performed).
    required: false
    default: 1
  fail_unreachable:
    description:
      - Determines whether to fail or not when the instance is unreachable.
    required: false
    default: true
  aws_access_key:
    description:
      - The AWS access key. If not set then the value of the 'AWS_ACCESS_KEY_ID'
        environment variable is used.
    required: false
    default: null
  aws_secret_key:
    description:
      - The AWS secret key. If not set then the value of the 'AWS_SECRET_ACCESS_KEY'
        environment variable is used.
    required: false
    default: null
author: Eyal Roth (@eyalroth)
'''

EXAMPLES = '''
# Perform a health check every 5 seconds up to a minute
- ec2_healthcheck: instance_id=i-123456 region=us-east-1 interval=5 repeat=12

# Perform a health check but do not fail if the instance is unreachable
- ec2_healthcheck: instance_id=i-123456 region=us-east-1 interval=10
                    fail_unreachable=false
'''

import time

try:
    import boto.ec2
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False

class EC2HealthCheck(object):

    def check_health(self, instance_id, region, interval, repeat, access,
                        secret):


        if access is not None and secret is not None:
            conn = boto.ec2.connect_to_region(region,
                                                aws_access_key_id=access,
                                                aws_secret_access_key=secret)
        else:
            conn = boto.ec2.connect_to_region(region)

        if conn is None:
            raise Exception("Couldn't connect to AWS. Check the region name")

        status = conn.get_all_instance_status(instance_ids=[instance_id])

        count = 0
        while (count < repeat):
            count += 1

            if self._is_instance_reachable(status):
                return True

            time.sleep(interval)
            status = conn.get_all_instance_status(instance_ids=[instance_id])

        return False

    def _is_instance_reachable(self, status_list):

        if len(status_list) == 0:
            return False

        status = status_list[0]
        if status.instance_status.status != "ok":
            return False

        if status.state_name != 'running':
            return False

        if status.system_status.details['reachability'] != 'passed':
            return False

        return True

def main():

    module = AnsibleModule(
        argument_spec = dict(
            instance_id=dict(required=True, type='str'),
            region=dict(required=True, type='str'),
            interval=dict(required=True, type='int'),
            repeat=dict(required=False, type='int', default='1'),
            fail_unreachable=dict(required=False, type='bool', default=True),
            aws_access_key=dict(required=False, type='str'),
            aws_secret_key=dict(required=False, type='str')
        ),
        supports_check_mode=False
    )

    if not HAS_BOTO:
        module.fail_json(msg='boto required for this module')


    instance_id = module.params['instance_id']
    try :

        params = module.params

        reachable = EC2HealthCheck().check_health(instance_id,
            params.get('region'), params.get('interval'),
            params.get('repeat'), params.get('aws_access_key'),
            params.get('aws_secret_key'))

        if not reachable and params.get('fail_unreachable'):
            module.fail_json(msg="The following instance isn't reachable: " +
                            instance_id)

        msg = "The following instance is "
        if reachable:
            msg += "rechable "
        else:
            msg += "unreachable "
        module.exit_json(changed=False, stdout=msg + instance_id)
    except Exception, e:
        module.fail_json(
            msg="An error occurred while performing a health check on " +
            instance_id + " | error: " + str(e))

from ansible.module_utils.basic import *
main()
