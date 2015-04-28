# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import shutil
import sys
import tempfile
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskNoMasterBranchtests(tests.Modeltests):
    """ Tests for flask application when the git repo has no master branch.
    """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskNoMasterBranchtests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.lib.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.fork.SESSION = self.session
        pagure.ui.repo.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = os.path.join(tests.HERE, 'repos')
        pagure.APP.config['FORK_FOLDER'] = os.path.join(tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            tests.HERE, 'requests')
        self.app = pagure.APP.test_client()

    def set_up_git_repo(self):
        """ Set up the git repo to play with. """

        # Create a git repo to play with
        gitrepo = os.path.join(tests.HERE, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        newpath = tempfile.mkdtemp(prefix='pagure-other-test')
        repopath = os.path.join(newpath, 'test')
        clone_repo = pygit2.clone_repository(gitrepo, repopath)

        # Create a file in that git repo
        with open(os.path.join(repopath, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        clone_repo.index.add('sources')
        clone_repo.index.write()

        # Commits the files added
        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        feature_branch = clone_repo.lookup_branch('feature')
        first_commit = feature_branch.get_object().hex

        # Second commit
        with open(os.path.join(repopath, '.gitignore'), 'w') as stream:
            stream.write('*~')
        clone_repo.index.add('.gitignore')
        clone_repo.index.write()

        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/master',
            author,
            committer,
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit]
        )

        refname = 'refs/heads/feature'
        ori_remote = clone_repo.remotes[0]
        ori_remote.push(refname)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_view_repo(self, send_email):
        """ Test the view_repo endpoint when the git repo has no master
        branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<h3>Last 0 commits</h3>', output.data)
        self.assertTrue(output.data.count('<a href="/test/branch/'), 1)

    @patch('pagure.lib.notify.send_email')
    def test_view_repo_branch(self, send_email):
        """ Test the view_repo_branch endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/branch/feature')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<h3>Last 1 commits</h3>', output.data)
        self.assertTrue(output.data.count('<a href="/test/branch/'), 1)

    @patch('pagure.lib.notify.send_email')
    def test_view_commits(self, send_email):
        """ Test the view_commits endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h3>Commits list</h3>\n    <ul>\n    </ul>', output.data)
        self.assertTrue(output.data.count('<a href="/test/branch/'), 1)

        output = self.app.get('/test/commits/feature')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<h3>Commits list</h3>', output.data)
        self.assertIn('Add sources file for testing', output.data)
        self.assertNotIn(
            '<h3>Commits list</h3>\n    <ul>\n    </ul>', output.data)
        self.assertTrue(output.data.count('<a href="/test/branch/'), 1)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskNoMasterBranchtests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)