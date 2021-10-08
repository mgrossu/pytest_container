from dataclasses import dataclass
from os import path
from pathlib import Path
from pytest_container.container import Container
from pytest_container.container import DerivedContainer
from pytest_container.runtime import ToParamMixin
from string import Template
from typing import Dict
from typing import Optional
from typing import Union


@dataclass(frozen=True)
class GitRepositoryBuild(ToParamMixin):
    """Test information storage for running builds using an external git
    repository. It is a required parameter for the `container_git_clone` and
    `host_git_clone` fixtures.
    """

    #: url of the git repository, can end with .git
    repository_url: str = ""
    #: an optional tag at which the repository should be checked out instead of
    #: using the default branch
    repository_tag: Optional[str] = None

    #: The command to run a "build" of the git repository inside a working
    #: copy.
    #: It can be left empty on purpose.
    build_command: str = ""

    def __post_init__(self) -> None:
        if not self.repository_url:
            raise ValueError("A repository url must be provided")

    def __str__(self) -> str:
        return self.repo_name

    @property
    def repo_name(self) -> str:
        """Name of the directory to which the repository will be checked out"""
        return path.basename(self.repository_url.replace(".git", ""))

    @property
    def clone_command(self) -> str:
        """Command to clone the repository at the appropriate tag"""
        clone_cmd_parts = ["git clone --depth 1"]
        if self.repository_tag:
            clone_cmd_parts.append(f"--branch {self.repository_tag}")
        clone_cmd_parts.append(self.repository_url)

        return " ".join(clone_cmd_parts)

    @property
    def test_command(self) -> str:
        """The full test command, including build_command and a cd into the
        correct folder.
        """
        cd_cmd = f"cd {self.repo_name}"
        if self.build_command:
            return f"{cd_cmd} && {self.build_command}"
        return cd_cmd


@dataclass
class MultiStageBuild:
    containers: Dict[str, Union[Container, DerivedContainer, str]]
    dockerfile_template: str

    @property
    def containerfile(self) -> str:
        return Template(self.dockerfile_template).substitute(
            **{k: str(v) for k, v in self.containers.items()}
        )

    def prepare_build(self, tmp_dir: Path, rootdir: Path):
        for _, container in self.containers.items():
            if not isinstance(container, str):
                container.prepare_container(rootdir)

        with open(tmp_dir / "Dockerfile", "w") as containerfile:
            containerfile.write(self.containerfile)
