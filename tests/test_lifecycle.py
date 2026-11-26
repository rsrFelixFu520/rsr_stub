"""Lifecycle sequencing and cleanup when a task fails."""

import pytest

from real2sim2real.job.base import AutoJob


def test_full_lifecycle_uses_component_instances_and_adjustments(monkeypatch):
    job = AutoJob.from_config()
    world, scene, robot, planner = job.sim_world, job.scene, job.robot, job.planner
    events = []

    def trace(obj, name, label):
        original = getattr(obj, name)

        def call(*args, **kwargs):
            events.append(label)
            return original(*args, **kwargs)

        monkeypatch.setattr(obj, name, call)

    for name in (
        "before_init_world_hook",
        "after_init_world_hook",
        "before_arrange_scene_hook",
        "build_occ",
        "after_arrange_scene_hook",
        "before_place_robot_hook",
        "after_place_robot_hook",
        "before_start_simulation_hook",
        "setup_gui_hook",
        "simulate",
        "after_start_simulation_hook",
    ):
        trace(job, name, name)
    for obj, prefix, names in (
        (world, "world", ("init_world", "destroy_world")),
        (scene, "scene", ("init_scene", "arrange", "adjust")),
        (robot, "robot", ("init_robot", "arrange", "adjust")),
        (planner, "planner", ("init_planner",)),
    ):
        for name in names:
            trace(obj, name, f"{prefix}.{name}")
    monkeypatch.setattr(job, "gui_inspect", lambda reason: events.append(f"gui.{reason}"))

    assert planner.state["ready"] is False
    job.run()
    job.close()
    assert events == [
        "before_init_world_hook",
        "world.init_world",
        "gui.after_init_world",
        "after_init_world_hook",
        "before_arrange_scene_hook",
        "build_occ",
        "scene.init_scene",
        "scene.arrange",
        "scene.adjust",
        "gui.after_arrange_scene",
        "after_arrange_scene_hook",
        "before_place_robot_hook",
        "robot.init_robot",
        "robot.arrange",
        "robot.adjust",
        "planner.init_planner",
        "gui.after_place_robot",
        "after_place_robot_hook",
        "before_start_simulation_hook",
        "setup_gui_hook",
        "gui.before_simulation",
        "simulate",
        "after_start_simulation_hook",
        "world.destroy_world",
    ]
    assert scene.sim_world is world
    assert robot.sim_world is world
    assert planner.robot is robot
    assert planner.state["ready"] is True
    assert job.sim_world is None
    assert world.app is world.world is world.stage is None


@pytest.mark.parametrize(
    ("component", "method", "after_hook"),
    [
        ("sim_world", "init_world", "after_init_world_hook"),
        ("scene", "arrange", "after_arrange_scene_hook"),
        ("planner", "init_planner", "after_place_robot_hook"),
        (None, "simulate", "after_start_simulation_hook"),
    ],
)
def test_failure_propagates_and_closes_once(monkeypatch, component, method, after_hook):
    job = AutoJob.from_config()
    events = []
    monkeypatch.setattr(job.sim_world, "destroy_world", lambda: events.append("closed"))
    monkeypatch.setattr(job, after_hook, lambda: events.append("after"))

    def fail(*args, **kwargs):
        raise RuntimeError("task failed")

    target = getattr(job, component) if component else job
    monkeypatch.setattr(target, method, fail)
    with pytest.raises(RuntimeError, match="task failed"):
        job.run()
    job.close()
    assert events == ["closed"]
    assert job.sim_world is None
