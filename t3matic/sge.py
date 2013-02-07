'''An (SSH-based) interface to a Grid Engine queue.'''

import sys
import math
import uuid
import tempfile
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
import paramiko
import utils
from cluster import ClusterStatus


class GEStatus(ClusterStatus):
    '''The status of a Grid Engine cluster.

    Just a paramiko wrapper to run q* commands and get some interesting
    information as Python objects.

    :param host: Head node hostname
    :param queue: Name of the GE queue to use
    '''
    def __init__(self, host, queue):
        self.queue = queue
        ClusterStatus.__init__(self, host, 'q')

    def rm(self, user):
        '''Remove all jobs for a user.

        :param user: User whose jobs to kill
        '''
        self._exec('qdel -u %s' % user)

    def users(self):
        '''See who is running how many jobs.

        :returns: {'username': (running, idle, other)} dict
        '''
        stdout, stderr = self._exec("qstat -u '*' -q %s" % self.queue)

        jobs = []
        for line in stdout.split('\n')[2:]:
            if len(line) == 0:
                continue
            try:
                _jobid, _prio, _script, user, state, _date, _time, _queue_slots = line.split(None, 7)
                jobs.append((user, state))
            except ValueError:
                continue

        users = {}
        for user, state in jobs:
            if user not in users:
                users[user] = [0, 0, 0]
            if state == 'r':
                users[user][0] += 1
            elif state == 'qw':
                users[user][1] += 1
            else:
                users[user][2] += 1

        return users

    def job_type_count(self, user, status=None, types=None, extract_macro_basename=True):
        '''Count the numbers of currently-running job commands.

        Answers questions like "how many copies of X simulation (rat x.mac) are running?"

        :param user: Full Condor username to show
        :param status: Show only jobs with this status (e.g. "R")
        :param types: Show only jobs with command names in this list
        :param extract_macro_basename: If True, use the RAT macro name as the command name
        :returns: {'command': count} dict
        '''
        stdout, stderr = self._exec("qstat -j '*' -xml -q %s" % self.queue)

        try:
            root = ET.fromstring(stdout)
        except ParseError:
            # GE returns invalid XML when the queue is empty
            return {}

        jobs = {}
        for _ in root.iter('detailed_job_info'):
            for dj in _.iter('djob_info'):
                for job in dj.iter('qmaster_response'):
                    if job.find('JB_owner').text != user:
                        continue
                    if status is not None and status != job.get('state'):
                        continue
                    args = map(lambda x: x.find('ST_name'), job.find('JB_job_args').findall('element'))
                    if args is None:
                        continue
                    cmd = args[1].text
                    if extract_macro_basename and 'rat' in cmd:
                        cmd = args[3].text.split('.', 3)[1]
                    jobs[cmd] = jobs.get(cmd, 0) + 1

        return jobs

    def job_durations(self, user, min_time=0):
        '''Get a list of job durations

        Useful for detecting problems. Only reports jobs with durations >= min_time.

        :param user: Full username to show
        :oaram min_time: Only show jobs running longer than min_time (seconds)
        :returns: {'job id': duration} dict
        '''
        stdout, stderr = self._exec("qstat -u '*' -q %s" % self.queue)

        min_time = timedelta(0, min_time)
        durations = {}

        for line in stdout.split('\n')[2:]:
            if len(line) == 0:
                continue

            jobid, _prio, _script, _user, state, date, time, _queue_slots = line.split(None, 7)

            if user != _user:
                continue

            duration = datetime.now() - datetime.strptime('%s %s' % (date, time), '%m/%d/%Y %H:%M:%S')
            if duration > min_time:
                durations[jobid] = duration.total_seconds()

        return durations

class RATGE(GEStatus):
    '''A GEStatus specific to running RAT jobs.'''
    def fill_queue(self, user, signals, target_queue_slots, initial_dir, exe_dir, output_location):
        '''Submit batch jobs to fill the queue up.

        If the number of running jobs falls below the target fullness, submit
        some more according to the rates specified in the signals dict.

        :param user: Cluster username
        :param signals: A signals dict, as from a config file
        :param target_queue_slots: The number of queue slots we should fill
        :param initial_dir: Working directory on the master for macros and such
        :param exe_dir: Directory on master containing rat_wrapper script
        :param output_location: Where to write output
        :returns: The number of jobs added
        '''
        norm = sum([v['rate'] for v in signals.values()])
        active_jobs = self.job_type_count(user=user)
        active_job_count = sum(active_jobs.values())

        if active_job_count >= 0.9 * target_queue_slots:
            return 0

        #submit_script_template = utils.MyTemplate(submit_script)

        jobs_added = 0

        for k, v in signals.items():
            job_count = int(math.ceil(1.0 * v['rate']/norm * target_queue_slots)) - active_jobs.get(k, 0)
            jobs_added += job_count
            job_id = uuid.uuid4().hex[:10]
            macro = 'macro.%s.%s.mac' % (k, job_id)

            if job_count <= 0:
                continue

            sub_line = utils.MyTemplate('q -q %{queue} %{exe_dir}/rat_wrapper.sh %{rat_version} %{initial_dir}/%{macro} -l /dev/null -o %{output_location}/%{name}-%{job_id}-%{id}.root')

            params = {
                'job_id': job_id,
                'name': k,
                'macro': macro,
                'rat_version': v['rat_version'],
                'output_location': output_location,
                'exe_dir': exe_dir,
                'initial_dir': initial_dir,
                'queue': self.queue
            }

            lines = []
            for i in range(job_count):
                params['id'] = i
                lines.append(sub_line.substitute(params))

            submit_script = '\n'.join(lines)

            with tempfile.NamedTemporaryFile() as f:
                f.write(submit_script)
                f.flush()
                self.sftp_put(f.name, '%s/submit_%s' % (initial_dir, job_id))

            with tempfile.NamedTemporaryFile() as f:
                f.write(v['macro'])
                f.flush()
                self.sftp_put(f.name, '%s/%s' % (initial_dir, macro))

            stdout, stderr = self._exec('bash %s/submit_%s' % (initial_dir, job_id))
            if len(stderr) > 0:
                sys.stderr.write('error with %s %s: %s' % (k, job_id, stderr))

        return jobs_added

