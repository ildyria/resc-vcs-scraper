# Standard Library
import json
import unittest
from datetime import datetime
from unittest.mock import ANY, patch

# Third Party
from fastapi.testclient import TestClient

# First Party
from resc_backend.constants import (
    RWS_ROUTE_BRANCHES,
    RWS_ROUTE_DISTINCT_PROJECTS,
    RWS_ROUTE_DISTINCT_REPOSITORIES,
    RWS_ROUTE_REPOSITORIES,
    RWS_VERSION_PREFIX
)
from resc_backend.db.model import DBbranch, DBfinding, DBrepository, DBscan, DBVcsInstance
from resc_backend.resc_web_service.api import app
from resc_backend.resc_web_service.dependencies import requires_auth, requires_no_auth
from resc_backend.resc_web_service.schema.repository import RepositoryCreate
from resc_backend.resc_web_service.schema.vcs_instance import VCSProviders


class TestRepositories(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[requires_auth] = requires_no_auth
        self.db_vcs_instance = []
        for i in range(1, 6):
            self.db_vcs_instance.append(DBVcsInstance(name=f"name{i}",
                                                      provider_type="BITBUCKET",
                                                      scheme="scheme",
                                                      hostname="hostname",
                                                      port=i,
                                                      organization="organization",
                                                      scope="scope",
                                                      exceptions="exceptions"))
            self.db_vcs_instance[i - 1].id_ = i

        self.db_repositories = []
        for i in range(1, 6):
            self.db_repositories.append(DBrepository(project_key=f"project_key_{i}",
                                                     repository_id=f"repository_id_{i}",
                                                     repository_name=f"repository_name_{i}",
                                                     repository_url=f"http://fake.repo.com/_{i}",
                                                     vcs_instance=i))
            self.db_repositories[i - 1].id_ = i

        self.db_branches = []
        for i in range(1, 6):
            self.db_branches.append(
                DBbranch(repository_id=i, branch_id=f"branch_id_{i}", branch_name=f"branch_name_{i}",
                         latest_commit=f"latest_commit_{i}"))
            self.db_branches[i - 1].id_ = i

        self.db_scans = []
        for i in range(1, 6):
            self.db_scans.append(DBscan(branch_id=i, scan_type="BASE",
                                        last_scanned_commit="FAKE_HASH", timestamp=datetime.utcnow(), rule_pack="1.2",
                                        increment_number=1))
            self.db_scans[i - 1].id_ = i

        self.db_findings = []
        for i in range(1, 6):
            self.db_findings.append(DBfinding(file_path=f"file_path_{i}",
                                              line_number=i,
                                              column_start=i,
                                              column_end=i,
                                              commit_id=f"commit_id_{i}",
                                              commit_message=f"commit_message_{i}",
                                              commit_timestamp=datetime.utcnow(),
                                              author=f"author_{i}",
                                              email=f"email_{i}",
                                              rule_name=f"rule_{i}",
                                              event_sent_on=datetime.utcnow(),
                                              branch_id=1))
            self.db_findings[i - 1].id_ = i

    @staticmethod
    def create_json_body(repository):
        return json.loads(
            TestRepositories.cast_db_repository_to_repository_create(repository).json())

    @staticmethod
    def cast_db_repository_to_repository_create(repository):
        return RepositoryCreate(project_key=repository.project_key,
                                repository_id=repository.repository_id,
                                repository_name=repository.repository_name,
                                repository_url=repository.repository_url,
                                vcs_instance=repository.vcs_instance)

    @staticmethod
    def assert_repository(data, repository):
        assert data["id_"] == repository.id_
        assert data["project_key"] == repository.project_key
        assert data["repository_id"] == repository.repository_id
        assert data["repository_name"] == repository.repository_name
        assert data["repository_url"] == repository.repository_url
        assert data["vcs_instance"] == repository.vcs_instance

    @patch("resc_backend.resc_web_service.crud.repository.create_repository_if_not_exists")
    def test_post_repositories(self, create_repository_if_not_exists):
        db_repository = self.db_repositories[0]
        create_repository_if_not_exists.return_value = db_repository
        response = self.client.post(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}",
                                    json=self.create_json_body(db_repository))
        assert response.status_code == 201, response.text
        self.assert_repository(response.json(), db_repository)
        create_repository_if_not_exists \
            .assert_called_once_with(db_connection=ANY,
                                     repository=self.cast_db_repository_to_repository_create(
                                         db_repository))

    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    def test_get_repositories_non_existing(self, get_repository):
        repository_id = 999
        get_repository.return_value = None
        response = self.client.get(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}/{repository_id}")
        assert response.status_code == 404, response.text
        get_repository.assert_called_once_with(ANY, repository_id=repository_id)

    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    def test_get_repositories(self, get_repository):
        repository_id = 0
        get_repository.return_value = self.db_repositories[repository_id]
        response = self.client.get(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}/{repository_id}")
        assert response.status_code == 200, response.text
        self.assert_repository(response.json(), self.db_repositories[repository_id])
        get_repository.assert_called_once_with(ANY, repository_id=repository_id)

    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    @patch("resc_backend.resc_web_service.crud.repository.update_repository")
    def test_put_repositories(self, update_repository, get_repository):
        repository_id = 1
        get_repository.return_value = self.db_repositories[repository_id]
        update_repository.return_value = self.db_repositories[1]
        update_repository.return_value.id_ = get_repository.return_value.id_
        response = self.client.put(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}/{repository_id}",
            json=self.create_json_body(self.db_repositories[1]))
        assert response.status_code == 200, response.text
        self.assert_repository(response.json(), self.db_repositories[1])
        get_repository.assert_called_once_with(ANY, repository_id=repository_id)
        update_repository \
            .assert_called_once_with(db_connection=ANY,
                                     repository=self.cast_db_repository_to_repository_create(
                                         self.db_repositories[1]), repository_id=repository_id)

    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    @patch("resc_backend.resc_web_service.crud.repository.delete_repository")
    def test_delete_repositories(self, delete_repository, get_repository):
        repository_id = 1
        get_repository.return_value = self.db_repositories[repository_id]
        response = self.client.delete(f"{RWS_VERSION_PREFIX}"
                                      f"{RWS_ROUTE_REPOSITORIES}/{repository_id}")
        assert response.status_code == 200, response.text
        get_repository.assert_called_once_with(ANY, repository_id=repository_id)
        delete_repository.assert_called_once_with(ANY, repository_id=repository_id, delete_related=True)

    @patch("resc_backend.resc_web_service.crud.repository.create_repository")
    def test_post_repositories_no_body(self, create_repository):
        response = self.client.post(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}")
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ["body"]
        assert data["detail"][0]["msg"] == "field required"
        create_repository.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.repository.create_repository")
    def test_post_repositories_empty_body(self, create_repository):
        response = self.client.post(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}",
                                    json={}, )
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ['body', 'project_key']
        assert data["detail"][0]["msg"] == "field required"
        assert data["detail"][1]["loc"] == ['body', 'repository_id']
        assert data["detail"][1]["msg"] == "field required"
        assert data["detail"][2]["loc"] == ['body', 'repository_name']
        assert data["detail"][2]["msg"] == "field required"
        assert data["detail"][3]["loc"] == ['body', 'repository_url']
        assert data["detail"][3]["msg"] == "field required"
        assert data["detail"][4]["loc"] == ['body', 'vcs_instance']
        assert data["detail"][4]["msg"] == "field required"
        create_repository.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    @patch("resc_backend.resc_web_service.crud.repository.update_repository")
    def test_put_repositories_empty_body(self, update_repository, get_repository):
        response = self.client.put(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}/9999999999", json={}, )
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ['body', 'project_key']
        assert data["detail"][0]["msg"] == "field required"
        assert data["detail"][1]["loc"] == ['body', 'repository_id']
        assert data["detail"][1]["msg"] == "field required"
        assert data["detail"][2]["loc"] == ['body', 'repository_name']
        assert data["detail"][2]["msg"] == "field required"
        assert data["detail"][3]["loc"] == ['body', 'repository_url']
        assert data["detail"][3]["msg"] == "field required"
        assert data["detail"][4]["loc"] == ['body', 'vcs_instance']
        assert data["detail"][4]["msg"] == "field required"
        update_repository.assert_not_called()
        get_repository.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    @patch("resc_backend.resc_web_service.crud.repository.update_repository")
    def test_put_repositories_non_existing(self, update_repository, get_repository):
        repository_id = 999
        get_repository.return_value = None
        response = self.client.put(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}/{repository_id}",
            json={"project_key": "dummy_project_key",
                  "repository_id": 47857774,
                  "repository_name": "updated_name",
                  "repository_url": "http://fake.repo.com",
                  "vcs_instance": 1
                  },
        )
        assert response.status_code == 404, response.text
        data = response.json()
        assert data["detail"] == "Repository not found"
        update_repository.assert_not_called()
        get_repository.assert_called_once_with(ANY, repository_id=repository_id)

    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    @patch("resc_backend.resc_web_service.crud.repository.update_repository")
    def test_delete_repositories_invalid(self, update_repository, get_repository):
        repository_id = 999
        get_repository.return_value = None
        response = self.client.delete(f"{RWS_VERSION_PREFIX}"
                                      f"{RWS_ROUTE_REPOSITORIES}/{repository_id}")
        assert response.status_code == 404, response.text
        data = response.json()
        assert data["detail"] == "Repository not found"
        get_repository.assert_called_once_with(ANY, repository_id=repository_id)
        update_repository.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.repository.get_repositories_count")
    @patch("resc_backend.resc_web_service.crud.repository.get_repositories")
    def test_get_multiple_repositories(self, get_repositories, get_repositories_count):
        get_repositories.return_value = self.db_repositories[:2]
        get_repositories_count.return_value = len(self.db_repositories[:2])
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}",
                                   params={"skip": 0, "limit": 5})
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["data"]) == 2
        self.assert_repository(data["data"][0], self.db_repositories[0])
        self.assert_repository(data["data"][1], self.db_repositories[1])
        assert data["total"] == 2
        assert data["limit"] == 5
        assert data["skip"] == 0

    @patch("resc_backend.resc_web_service.crud.repository.get_repositories")
    def test_get_multiple_repositories_with_negative_skip(self, get_repositories):
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}",
                                   params={"skip": -1, "limit": 5})
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ["query", "skip"]
        assert data["detail"][0]["msg"] == "ensure this value is greater than or equal to 0"
        get_repositories.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.repository.get_repositories")
    def test_get_multiple_repositories_with_negative_limit(self, get_repositories):
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}",
                                   params={"skip": 0, "limit": -1})
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ["query", "limit"]
        assert data["detail"][0]["msg"] == "ensure this value is greater than or equal to 1"
        get_repositories.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.finding.get_total_findings_count")
    @patch("resc_backend.resc_web_service.crud.scan.get_latest_scan_for_branch")
    @patch("resc_backend.resc_web_service.crud.branch.get_branches_for_repository")
    @patch("resc_backend.resc_web_service.crud.branch.get_branches_count_for_repository")
    @patch("resc_backend.resc_web_service.crud.scan.get_scans")
    def test_get_repository_branches(self, get_scans, get_branches_count_for_repository,
                                     get_branches_for_repository, get_latest_scan_for_branch,
                                     get_total_findings_count):
        get_branches_for_repository.return_value = self.db_branches
        get_branches_count_for_repository.return_value = len(self.db_branches)
        get_latest_scan_for_branch.return_value = self.db_scans[1]
        get_scans.return_value = self.db_scans
        get_total_findings_count.return_value = len(self.db_findings)
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}/1{RWS_ROUTE_BRANCHES}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["data"][0]["id_"] == self.db_branches[0].id_
        assert datetime.strptime(data["data"][0]["last_scan_datetime"], "%Y-%m-%dT%H:%M:%S.%f") == \
               self.db_scans[3].timestamp
        assert data["total"] == 5
        assert data["limit"] == 100
        assert data["skip"] == 0

    @patch("resc_backend.resc_web_service.crud.branch.get_branches_for_repository")
    @patch("resc_backend.resc_web_service.crud.branch.get_branches_count_for_repository")
    def test_get_repository_branches_non_existing(self, get_branches_count_for_repository,
                                                  get_branches_for_repository):
        get_branches_for_repository.return_value = []
        get_branches_count_for_repository.return_value = 0
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}/9999{RWS_ROUTE_BRANCHES}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0
        assert data["limit"] == 100
        assert data["skip"] == 0

    def test_get_repository_branches_invalid_id(self):
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}/invalid{RWS_ROUTE_BRANCHES}")
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ['path', 'repository_id']
        assert data["detail"][0]["msg"] == "value is not a valid integer"
        assert data["detail"][0]["type"] == "type_error.integer"

    @patch("resc_backend.resc_web_service.crud.repository.get_distinct_projects")
    def test_get_distinct_projects_when_single_vcs_instance_selected(self, get_distinct_projects):
        get_distinct_projects.return_value = self.db_repositories
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}{RWS_ROUTE_DISTINCT_PROJECTS}/?"
                                   f"vcsprovider={VCSProviders.BITBUCKET}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == len(self.db_repositories)
        assert data[0] == self.db_repositories[0].project_key
        assert data[1] == self.db_repositories[1].project_key
        assert data[2] == self.db_repositories[2].project_key
        assert data[3] == self.db_repositories[3].project_key
        assert data[4] == self.db_repositories[4].project_key

    @patch("resc_backend.resc_web_service.crud.repository.get_distinct_projects")
    def test_get_distinct_projects_when_multiple_vcs_instance_selected(self, get_distinct_projects):
        get_distinct_projects.return_value = self.db_repositories
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}{RWS_ROUTE_DISTINCT_PROJECTS}/?"
                                   f"vcsprovider={VCSProviders.BITBUCKET}"
                                   f"&vcsprovider={VCSProviders.AZURE_DEVOPS}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == len(self.db_repositories)
        assert data[0] == self.db_repositories[0].project_key
        assert data[1] == self.db_repositories[1].project_key
        assert data[2] == self.db_repositories[2].project_key
        assert data[3] == self.db_repositories[3].project_key
        assert data[4] == self.db_repositories[4].project_key

    @patch("resc_backend.resc_web_service.crud.repository.get_distinct_projects")
    def test_get_distinct_projects_by_repository_filter(self, get_distinct_projects):
        repository_name = "Test_Repository"
        get_distinct_projects.return_value = self.db_repositories
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}{RWS_ROUTE_DISTINCT_PROJECTS}/?"
                                   f"repositoryfilter={repository_name}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == len(self.db_repositories)
        assert data[0] == self.db_repositories[0].project_key
        assert data[1] == self.db_repositories[1].project_key
        assert data[2] == self.db_repositories[2].project_key
        assert data[3] == self.db_repositories[3].project_key
        assert data[4] == self.db_repositories[4].project_key

    @patch("resc_backend.resc_web_service.crud.repository.get_distinct_projects")
    def test_get_distinct_projects_by_vcs_instance_and_repository_filter(self, get_distinct_projects):
        repository_name = "Test_Repository"
        get_distinct_projects.return_value = self.db_repositories
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}{RWS_ROUTE_DISTINCT_PROJECTS}/?"
                                   f"vcsprovider={VCSProviders.BITBUCKET}"
                                   f"&repositoryfilter={repository_name}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == len(self.db_repositories)
        assert data[0] == self.db_repositories[0].project_key
        assert data[1] == self.db_repositories[1].project_key
        assert data[2] == self.db_repositories[2].project_key
        assert data[3] == self.db_repositories[3].project_key
        assert data[4] == self.db_repositories[4].project_key

    @patch("resc_backend.resc_web_service.crud.repository.get_distinct_projects")
    def test_get_distinct_projects_when_no_filter_selected(self, get_distinct_projects):
        get_distinct_projects.return_value = self.db_repositories
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}{RWS_ROUTE_DISTINCT_PROJECTS}/")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == len(self.db_repositories)
        assert data[0] == self.db_repositories[0].project_key
        assert data[1] == self.db_repositories[1].project_key
        assert data[2] == self.db_repositories[2].project_key
        assert data[3] == self.db_repositories[3].project_key
        assert data[4] == self.db_repositories[4].project_key

    @patch("resc_backend.resc_web_service.crud.repository.get_distinct_repositories")
    def test_get_distinct_repositories_when_single_vcs_instance_selected(self, get_distinct_repositories):
        get_distinct_repositories.return_value = self.db_repositories
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}{RWS_ROUTE_DISTINCT_REPOSITORIES}/?"
                                   f"vcsprovider={VCSProviders.BITBUCKET}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == len(self.db_repositories)
        assert data[0] == self.db_repositories[0].repository_name
        assert data[1] == self.db_repositories[1].repository_name
        assert data[2] == self.db_repositories[2].repository_name
        assert data[3] == self.db_repositories[3].repository_name
        assert data[4] == self.db_repositories[4].repository_name

    @patch("resc_backend.resc_web_service.crud.repository.get_distinct_repositories")
    def test_get_distinct_repositories_when_multiple_vcs_instance_selected(self, get_distinct_repositories):
        get_distinct_repositories.return_value = self.db_repositories
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}{RWS_ROUTE_DISTINCT_REPOSITORIES}/?"
                                   f"vcsprovider={VCSProviders.BITBUCKET}"
                                   f"&vcsprovider={VCSProviders.AZURE_DEVOPS}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == len(self.db_repositories)
        assert data[0] == self.db_repositories[0].repository_name
        assert data[1] == self.db_repositories[1].repository_name
        assert data[2] == self.db_repositories[2].repository_name
        assert data[3] == self.db_repositories[3].repository_name
        assert data[4] == self.db_repositories[4].repository_name

    @patch("resc_backend.resc_web_service.crud.repository.get_distinct_repositories")
    def test_get_distinct_repositories_by_project_name(self, get_distinct_repositories):
        project_name = "Test_Project"
        get_distinct_repositories.return_value = self.db_repositories
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}{RWS_ROUTE_DISTINCT_REPOSITORIES}/?"
                                   f"projectname={project_name}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == len(self.db_repositories)
        assert data[0] == self.db_repositories[0].repository_name
        assert data[1] == self.db_repositories[1].repository_name
        assert data[2] == self.db_repositories[2].repository_name
        assert data[3] == self.db_repositories[3].repository_name
        assert data[4] == self.db_repositories[4].repository_name

    @patch("resc_backend.resc_web_service.crud.repository.get_distinct_repositories")
    def test_get_distinct_repositories_by_vcs_instance_and_project_name(self, get_distinct_repositories):
        project_name = "Test_Project"
        get_distinct_repositories.return_value = self.db_repositories
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}{RWS_ROUTE_DISTINCT_REPOSITORIES}/?"
                                   f"vcsprovider={VCSProviders.BITBUCKET}"
                                   f"&projectname={project_name}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == len(self.db_repositories)
        assert data[0] == self.db_repositories[0].repository_name
        assert data[1] == self.db_repositories[1].repository_name
        assert data[2] == self.db_repositories[2].repository_name
        assert data[3] == self.db_repositories[3].repository_name
        assert data[4] == self.db_repositories[4].repository_name

    @patch("resc_backend.resc_web_service.crud.repository.get_distinct_repositories")
    def test_get_distinct_repositories_when_no_filter_selected(self, get_distinct_repositories):
        get_distinct_repositories.return_value = self.db_repositories
        response = self.client.get(f"{RWS_VERSION_PREFIX}"
                                   f"{RWS_ROUTE_REPOSITORIES}{RWS_ROUTE_DISTINCT_REPOSITORIES}/")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == len(self.db_repositories)
        assert data[0] == self.db_repositories[0].repository_name
        assert data[1] == self.db_repositories[1].repository_name
        assert data[2] == self.db_repositories[2].repository_name
        assert data[3] == self.db_repositories[3].repository_name
        assert data[4] == self.db_repositories[4].repository_name

    @patch("resc_backend.resc_web_service.crud."
           "repository.get_findings_metadata_by_repository_id")
    @patch("resc_backend.resc_web_service.crud.repository.get_repositories_count")
    @patch("resc_backend.resc_web_service.crud.repository.get_repositories")
    def test_get_all_repositories_with_findings_metadata(self, get_repositories, get_repositories_count,
                                                         get_findings_metadata_by_repository_id):
        get_repositories.return_value = self.db_repositories[:2]
        get_repositories_count.return_value = len(self.db_repositories[:2])
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}",
                                   params={"skip": 0, "limit": 5})
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["data"]) == 2
        self.assert_repository(data["data"][0], self.db_repositories[0])
        self.assert_repository(data["data"][1], self.db_repositories[1])
        assert data["total"] == 2
        assert data["limit"] == 5
        assert data["skip"] == 0

        mocked_findings_meta_data = {
            "data": {
                "project_key": "dummmy_project",
                "repository_id": "r2",
                "repository_name": "dummy_repo",
                "repository_url": "https://fake-ado.com",
                "vcs_instance": "AZURE_DEVOPS",
                "id_": 1
            },
            "true_positive": 1,
            "false_positive": 2,
            "not_analyzed": 3,
            "under_review": 4,
            "clarification_required": 5,
            "total_findings_count": 15
        }

        get_findings_metadata_by_repository_id.return_value = mocked_findings_meta_data
        response = get_findings_metadata_by_repository_id.return_value
        assert response["data"]["project_key"] == "dummmy_project"
        assert response["data"]["repository_id"] == "r2"
        assert response["data"]["repository_name"] == "dummy_repo"
        assert response["data"]["repository_url"] == "https://fake-ado.com"
        assert response["data"]["vcs_instance"] == "AZURE_DEVOPS"
        assert response["data"]["id_"] == 1
        assert response["true_positive"] == 1
        assert response["false_positive"] == 2
        assert response["not_analyzed"] == 3
        assert response["under_review"] == 4
        assert response["clarification_required"] == 5
        assert response["total_findings_count"] == 15

    @patch("resc_backend.resc_web_service.crud.repository"
           ".get_findings_metadata_by_repository_id")
    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    def test_get_findings_metadata_for_repository(self, get_repository,
                                                  get_findings_metadata_by_repository_id):
        repository_id = 1
        get_repository.return_value = self.db_repositories[repository_id]
        response = self.client.get(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}/{repository_id}")
        assert response.status_code == 200, response.text
        self.assert_repository(response.json(), self.db_repositories[repository_id])
        get_repository.assert_called_once_with(ANY, repository_id=repository_id)

        mocked_findings_meta_data = {"true_positive": 1, "false_positive": 2,
                                     "not_analyzed": 3,
                                     "under_review": 4, "clarification_required": 5,
                                     "total_findings_count": 15}
        get_findings_metadata_by_repository_id.return_value = mocked_findings_meta_data
        response = get_findings_metadata_by_repository_id.return_value
        assert response["true_positive"] == 1
        assert response["false_positive"] == 2
        assert response["not_analyzed"] == 3
        assert response["under_review"] == 4
        assert response["clarification_required"] == 5
        assert response["total_findings_count"] == 15

    @patch("resc_backend.resc_web_service.crud"
           ".repository.get_findings_metadata_by_repository_id")
    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    def test_get_findings_metadata_for_repository_non_existing(self,
                                                               get_repository,
                                                               get_findings_metadata_by_repository_id):
        repository_id = 999
        get_repository.return_value = None
        response = self.client.get(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_REPOSITORIES}/{repository_id}")
        assert response.status_code == 404, response.text
        get_repository.assert_called_once_with(ANY, repository_id=repository_id)
        get_findings_metadata_by_repository_id.assert_not_called()
