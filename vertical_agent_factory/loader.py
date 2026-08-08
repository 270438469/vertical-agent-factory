from pathlib import Path

import yaml

from .errors import PackageValidationError


def _yaml(path, required=True):
    path = Path(path)
    if not path.exists():
        if required:
            raise PackageValidationError("Missing required file: {}".format(path))
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _yaml_files(path):
    path = Path(path)
    if not path.exists():
        return []
    return [_yaml(item) for item in sorted(path.glob("*.yaml"))]


class DomainPackage(object):
    def __init__(self, project_root, domain_id):
        self.project_root = Path(project_root).resolve()
        self.domain_id = domain_id
        domain_root = self.project_root / "domains" / domain_id
        self.domain_root = domain_root
        self.domain = _yaml(domain_root / "domain.yaml")
        self.ontology = _yaml(domain_root / "ontology.yaml")
        self.tasks = _yaml(domain_root / "task-taxonomy.yaml").get("tasks", [])
        self.knowledge = _yaml(domain_root / "knowledge.yaml", required=False)
        self.agent = _yaml(self.project_root / "agents" / domain_id / "agent.yaml")
        self.capabilities = _yaml(
            self.project_root / "capabilities" / "{}.yaml".format(domain_id)
        ).get("capabilities", [])
        self.bindings = _yaml(
            self.project_root / "mcp" / "bindings" / "{}.yaml".format(domain_id)
        ).get("bindings", [])
        self.policies = _yaml_files(self.project_root / "policies" / domain_id)
        self.workflows = _yaml_files(domain_root / "workflows")
        self.skills = []
        skills_root = self.project_root / "skills" / domain_id
        if skills_root.exists():
            for skill_file in sorted(skills_root.glob("*/skill.yaml")):
                skill = _yaml(skill_file)
                skill["_path"] = str(skill_file.parent)
                self.skills.append(skill)
        self.evals = []
        for eval_doc in _yaml_files(self.project_root / "evals" / domain_id):
            if "cases" in eval_doc:
                self.evals.extend(eval_doc["cases"])
            else:
                self.evals.append(eval_doc)

    def task(self, task_id):
        return self._by_id(self.tasks, task_id, "task")

    def skill(self, skill_id):
        return self._by_id(self.skills, skill_id, "skill")

    def capability(self, capability_id):
        return self._by_id(self.capabilities, capability_id, "capability")

    def workflow(self, workflow_id):
        return self._by_id(self.workflows, workflow_id, "workflow")

    def bindings_for(self, capability_id):
        return [item for item in self.bindings if item.get("capability") == capability_id]

    @staticmethod
    def _by_id(items, item_id, kind):
        for item in items:
            if item.get("id") == item_id:
                return item
        raise PackageValidationError("Unknown {}: {}".format(kind, item_id))


def load_domain_package(project_root, domain_id):
    return DomainPackage(project_root, domain_id)
