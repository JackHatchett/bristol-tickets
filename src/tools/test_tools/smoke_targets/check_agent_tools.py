"""smoke_targets/check_agent_tools.py — the `agent_tools` smoke target, run by smoke.py."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from qt_headless import TOOLS
from smoke_targets.failure import SmokeFailure


def check_agent_tools() -> list[str]:
    """Creating and editing an agent, and what an edit carries through.

    An agent is a charter document and a config entry, and the property worth
    guarding is that they cannot drift apart: one call writes both, a refused
    call writes neither, and every key an entry contains survives an edit — the one
    this build knows nothing about included, because a form that silently drops
    what it does not recognize is worse than one that refuses.
    """
    import shutil

    ok: list[str] = []
    root = TOOLS.parent.parent
    agent_tools = TOOLS / "agent_tools"

    def run(script: str, *args: str, cwd: Path):
        done = subprocess.run(
            [sys.executable, str(cwd / "src" / "tools" / "agent_tools" / script), *args],
            capture_output=True,
            text=True,
            cwd=str(cwd),
        )
        return done.returncode, done.stdout, done.stderr

    sys.path.insert(0, str(agent_tools))
    import agents as agent_reader

    # A charter is read whole, so what the reader returns is the file. Nothing
    # is parsed, so no charter can be one the tool declines to handle.
    configured = agent_reader.list_agents()
    if not configured:
        raise SmokeFailure("this installation configures no agents")
    for agent in configured:
        on_disk = (root / agent["identity"]).read_text(encoding="utf-8")
        if agent["charter"] != on_disk:
            raise SmokeFailure(f"{agent['slug']}'s charter did not read back as its file")
        if agent["charter_error"]:
            raise SmokeFailure(f"{agent['slug']}'s charter is unreadable: {agent['charter_error']}")
    ok.append(f"all {len(configured)} charters read back as the files they are")

    # Every key an entry contains reaches the reader, under a name of its own or
    # in `extra`. A key that reached neither would be one an edit could drop.
    import read_config as config_reader

    for slug, entry in config_reader.get("agents", {}).items():
        if slug == "_notes":
            continue
        read = agent_reader.read_agent(slug)
        for key in entry:
            named = {
                "identity",
                "description",
                "key_data_paths",
                "key_context_files",
                "notebook_access",
                "dashboard_access",
                "skills",
                "env",
            }
            if key not in named and key not in read["extra"]:
                raise SmokeFailure(f"{slug}'s '{key}' reaches neither a field nor extra")
        if read["notebook_access"] != (entry.get("notebook_access") or {}):
            raise SmokeFailure(f"{slug}'s notebook access was not read verbatim")
    ok.append("every key every entry contains reaches a field of its own or extra")

    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "clone"
        (scratch / "src").mkdir(parents=True)
        shutil.copytree(TOOLS, scratch / "src" / "tools")
        shutil.copytree(root / "src" / "templates", scratch / "src" / "templates")
        shutil.copy(root / "src" / "app.md", scratch / "src" / "app.md")
        (scratch / "src" / "agent_identities").mkdir()
        (scratch / "config").mkdir()
        config_file_path = scratch / "config" / "config.local.json"
        config_file_path.write_text(json.dumps({"active_agent": "chief_of_staff", "agents": {}}))
        slug = "smoke_agent"

        # The starting charter comes from the template that owns the shape.
        code, body, err = run("agents.py", "skeleton", slug, cwd=scratch)
        if code != 0 or "Agent Charter" not in body:
            raise SmokeFailure(f"no starting charter: {(err or body).strip()}")
        if "{{" in body:
            raise SmokeFailure("the starting charter carries template braces")
        written = Path(tmp) / "charter.md"
        typed = body + "\n## 4. A section the template never had\n\nProse.\n"
        written.write_text(typed)

        code, out, err = run(
            "create_agent.py",
            slug,
            "--description",
            "A scratch agent, made by the smoke check.",
            "--charter-file",
            str(written),
            "--env",
            "SMOKE_HOME=/nowhere",
            "--notebook",
            "read",
            "--no-epic",
            cwd=scratch,
        )
        if code != 0:
            raise SmokeFailure(f"creating an agent failed: {(err or out).strip()}")
        charter = scratch / "src" / "agent_identities" / f"{slug}.md"
        if charter.read_text() != typed:
            raise SmokeFailure("the charter was not written as it was typed")
        stored = json.loads(config_file_path.read_text())
        if slug not in stored.get("agents", {}):
            raise SmokeFailure("an agent was created with no config entry")
        if stored["agents"][slug].get("env") != {"SMOKE_HOME": "/nowhere"}:
            raise SmokeFailure("the environment did not reach the config entry")
        ok.append("create writes the charter verbatim and the config entry beside it")

        # A key this build knows nothing about, planted by hand the way an
        # older or newer build would leave one.
        stored["agents"][slug]["lesson_pipeline"] = {"stages": 4}
        config_file_path.write_text(json.dumps(stored, indent=2))
        code, out, _ = run("agents.py", "read", slug, "--json", cwd=scratch)
        if json.loads(out)["extra"] != {"lesson_pipeline": {"stages": 4}}:
            raise SmokeFailure("an unknown key did not reach extra")

        was_charter = charter.read_text()
        was_config = config_file_path.read_text()
        code, _, err = run("agents.py", "edit", slug, "--description", "", cwd=scratch)
        if code == 0:
            raise SmokeFailure("an agent was left with no description")
        if charter.read_text() != was_charter or config_file_path.read_text() != was_config:
            raise SmokeFailure("a refused edit still wrote")
        ok.append("a refused edit leaves both the charter and the entry as they were")

        edited = typed.replace("Prose.", "Prose, revised.")
        written.write_text(edited)
        code, out, err = run(
            "agents.py",
            "edit",
            slug,
            "--description",
            "A scratch agent, renamed.",
            "--charter-file",
            str(written),
            "--data-path",
            "data/scratch",
            "--read-path",
            "data/reference",
            "--notebook-mode",
            "per_folder",
            "--notebook-folder",
            "inbox=write",
            "--notebook-folder",
            "journal=read",
            "--env",
            "SMOKE_HOME=/elsewhere",
            cwd=scratch,
        )
        if code != 0:
            raise SmokeFailure(f"editing an agent failed: {(err or out).strip()}")
        code, out, _ = run("agents.py", "read", slug, "--json", cwd=scratch)
        after = json.loads(out)
        if after["charter"] != edited:
            raise SmokeFailure("the edited charter is not what was supplied")
        if after["description"] != "A scratch agent, renamed.":
            raise SmokeFailure("the description did not reach the entry")
        if after["notebook_access"] != {
            "mode": "per_folder",
            "folders": {"inbox": "write", "journal": "read"},
        }:
            raise SmokeFailure(f"notebook access is not what was set: {after['notebook_access']}")
        if after["env"] != {"SMOKE_HOME": "/elsewhere"}:
            raise SmokeFailure("the environment did not survive the edit")
        if after["extra"] != {"lesson_pipeline": {"stages": 4}}:
            raise SmokeFailure("an unknown key was dropped by an edit")
        ok.append(
            "one edit reaches the charter and every key of the entry, "
            "and carries an unknown key through untouched"
        )

        # A folder an agent reaches carries the access granted in it, the two
        # options fill one list in the order given, and an entry written before
        # access was recorded still reads as the write it was.
        granted = [
            {"path": "data/scratch", "access": "write"},
            {"path": "data/reference", "access": "read"},
        ]
        if after["key_data_paths"] != granted:
            raise SmokeFailure(
                f"the folder grants are not what was granted: {after['key_data_paths']}"
            )
        planted = json.loads(config_file_path.read_text())
        planted["agents"][slug]["key_data_paths"] = ["data/from_an_older_build"]
        config_file_path.write_text(json.dumps(planted, indent=2))
        code, out, _ = run("agents.py", "read", slug, "--json", cwd=scratch)
        if json.loads(out)["key_data_paths"] != [
            {"path": "data/from_an_older_build", "access": "write"}
        ]:
            raise SmokeFailure("a bare folder path did not read as a write grant")
        code, out, err = run("agents.py", "edit", slug, "--no-data-paths", cwd=scratch)
        if code != 0:
            raise SmokeFailure(f"emptying the grants failed: {(err or out).strip()}")
        code, out, _ = run("agents.py", "read", slug, "--json", cwd=scratch)
        if json.loads(out)["key_data_paths"]:
            raise SmokeFailure("--no-data-paths left a grant behind")
        code, out, err = run(
            "agents.py",
            "edit",
            slug,
            "--data-path",
            "data/scratch",
            "--read-path",
            "data/reference",
            cwd=scratch,
        )
        if code != 0:
            raise SmokeFailure(f"regranting failed: {(err or out).strip()}")
        ok.append(
            "a folder grant carries its access, a bare path reads as a "
            "write, and the list can be emptied and granted again"
        )

        moved = "src/agent_identities/moved_smoke_agent.md"
        code, out, err = run("agents.py", "edit", slug, "--identity", moved, cwd=scratch)
        if code != 0:
            raise SmokeFailure(f"moving a charter failed: {(err or out).strip()}")
        if charter.exists():
            raise SmokeFailure("a moved charter was left behind at its old path")
        if (scratch / moved).read_text() != edited:
            raise SmokeFailure("a moved charter did not arrive whole")
        ok.append("the charter file can be moved, and the old path is gone")

        code, out, _ = run("agents.py", "list", "--json", cwd=scratch)
        again = json.loads(out)
        if (
            [a["slug"] for a in again] != [slug]
            or again[0]["charter"] != edited
            or again[0]["identity"] != moved
        ):
            raise SmokeFailure("a fresh read did not find what was entered")
        ok.append("a fresh read finds the agent and everything entered into it")

        # An agent adopted from a file keeps its charter with the user's data,
        # never in the published tree, and its tokens resolve to this
        # installation's own names. Its writes are pinned to the scratch data
        # root, so the board it opens an epic on is the scratch one.
        planted = json.loads(config_file_path.read_text())
        planted["imported_agents"] = {"install_dir": "data/smoke/agents"}
        config_file_path.write_text(json.dumps(planted, indent=2))
        agent_file = Path(tmp) / "addon_smoke.agent.json"
        agent_file.write_text(
            json.dumps(
                {
                    "bristol_agent": 1,
                    "slug": "addon_smoke",
                    "charter": "# addon_smoke.md — Agent Charter\n",
                    "entry": {
                        "description": "An add-on.",
                        "key_data_paths": [{"path": "data/<instance>/addon", "access": "write"}],
                        "env": {"ADDON_HOME": "<supply>"},
                    },
                    "skills": [],
                }
            )
        )
        pinned = {**os.environ, "DATA_ROOT": str(scratch / "data"), "INSTANCE_SLUG": "smoke"}
        importer = scratch / "src" / "tools" / "agent_tools" / "import_agent.py"
        for extra in ([], ["--accept"]):
            done = subprocess.run(
                [sys.executable, str(importer), str(agent_file), *extra],
                capture_output=True,
                text=True,
                cwd=str(scratch),
                env=pinned,
            )
            if done.returncode != 0:
                raise SmokeFailure(
                    f"import_agent {' '.join(extra) or 'read'} "
                    f"failed: {(done.stderr or done.stdout).strip()}"
                )
            if not extra and "addon_smoke" in json.loads(config_file_path.read_text())["agents"]:
                raise SmokeFailure("reading an agent file wrote the agent")
        if (scratch / "src" / "agent_identities" / "addon_smoke.md").exists():
            raise SmokeFailure("an imported charter was written into the published tree")
        imported = json.loads(config_file_path.read_text())["agents"]["addon_smoke"]
        if (
            imported["identity"] != "data/smoke/agents/addon_smoke.md"
            or not (scratch / imported["identity"]).is_file()
        ):
            raise SmokeFailure(
                f"the imported charter is not where config says: {imported['identity']}"
            )
        if imported["key_data_paths"] != [{"path": "data/smoke/addon", "access": "write"}]:
            raise SmokeFailure("an agent file's instance token did not resolve")
        ok.append(
            "an imported agent's charter lands in the data folder, and its "
            "instance token resolves to this installation's"
        )

    # Every agent file Bristol ships reads as one, and each skill it fetches is
    # named by a folder address the importer can resolve.
    sys.path.insert(0, str(TOOLS / "skill_tools"))
    import import_agent

    import skills as skill_loader

    shipped = sorted((root / "src" / "addons").glob("*.agent.json"))
    for agent_file in shipped:
        document = import_agent.load(agent_file)
        for record in document.get("skills", []):
            if record.get("source") == "address":
                skill_loader.resolve_address(record["address"])
            elif record.get("source") != "native":
                raise SmokeFailure(
                    f"{agent_file.name} names {record.get('name')} with no address to fetch it from"
                )
    ok.append(
        f"{len(shipped)} shipped agent files read, and every skill in "
        f"them has an address or ships with Bristol"
    )

    # Neither tool can reach a network or a model: the whole point of the form
    # is that an agent can be made with the machine offline.
    reaches_out = ("socket", "urllib", "http.client", "requests", "ssl", "anthropic", "openai")
    for script in ("create_agent.py", "agents.py"):
        source = (agent_tools / script).read_text()
        for name in reaches_out:
            if re.search(rf"^\s*(?:import|from)\s+{re.escape(name)}\b", source, re.M):
                raise SmokeFailure(f"{script} imports {name}")
    ok.append("neither agent tool imports anything that reaches a network or a model")
    return ok
