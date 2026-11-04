import math
import random
import tempfile
import wave
from itertools import product

import numpy as np
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from direct.filter.CommonFilters import CommonFilters
from direct.task import Task
from panda3d.core import (
    AmbientLight,
    CardMaker,
    ClockObject,
    Geom,
    GeomLines,
    GeomNode,
    GeomPoints,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    LineSegs,
    Material,
    NodePath,
    TextNode,
    Vec3,
    Vec4,
    WindowProperties,
    loadPrcFileData,
)


loadPrcFileData("", "win-size 1600 900")
loadPrcFileData("", "fullscreen true")
loadPrcFileData("", "sync-video false")
loadPrcFileData("", "show-frame-rate-meter false")
loadPrcFileData("", "framebuffer-multisample 1")
loadPrcFileData("", "multisamples 4")


PLANE_RATES = {
    (0, 1): 0.23,
    (0, 2): -0.17,
    (0, 3): 0.31,
    (1, 2): 0.14,
    (1, 3): -0.21,
    (2, 3): 0.27,
}


def make_sphere(parent, position, scale, color, name="sphere"):
    node = loader.loadModel("models/misc/sphere")
    node.setName(name)
    node.reparentTo(parent)
    node.setPos(*position)
    node.setScale(scale)
    node.setColor(*color)
    node.setLightOff()
    material = Material()
    material.setEmission(Vec4(*color))
    material.setDiffuse(Vec4(*color))
    node.setMaterial(material, 1)
    return node


def add_ring(parent, center, radius, color, thickness=1.4, segments=220):
    lines = LineSegs()
    lines.setThickness(thickness)
    lines.setColor(*color)
    for index in range(segments + 1):
        angle = math.tau * index / segments
        point = (radius * math.cos(angle), 0.0, radius * math.sin(angle))
        if index == 0:
            lines.moveTo(*point)
        else:
            lines.drawTo(*point)
    ring = parent.attachNewNode(lines.create())
    ring.setPos(*center)
    ring.setLightOff()
    return ring


class TesseractJourney(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(0.003, 0.006, 0.016, 1)
        self.camLens.setFov(76)
        self.camLens.setNearFar(0.08, 1400)
        self.camera.setPos(0, 0, 0)
        self.camera.setHpr(0, 0, 0)
        self.filters = CommonFilters(self.win, self.cam)
        self.filters.setBloom(
            blend=(0.28, 0.42, 0.55, 0.0),
            desat=0.0,
            intensity=1.25,
            size="medium",
            mintrigger=0.36,
            maxtrigger=1.0,
        )

        self.phase = "VOYAGE 01  /  THE OUTER DARK"
        self.phase_time = 0.0
        self.total_time = 0.0
        self.keys = set()
        self.hud_visible = True
        self.mouse_captured = True
        self._make_lights()
        self._make_stars()
        self._make_black_hole()
        self._make_tesseract()
        self._make_architecture()
        self._make_hud()
        self._make_audio()
        self._bind_controls()
        self._set_mouse_capture(True)
        self.taskMgr.add(self.update, "journey-update")

    def _make_lights(self):
        ambient = AmbientLight("cosmic-ambient")
        ambient.setColor(Vec4(0.22, 0.28, 0.42, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

    def _make_stars(self):
        rng = random.Random(22)
        count = 5200
        data = GeomVertexData("far-stars", GeomVertexFormat.getV3c4(), Geom.UHStatic)
        data.setNumRows(count)
        vertices = GeomVertexWriter(data, "vertex")
        colors = GeomVertexWriter(data, "color")
        points = GeomPoints(Geom.UHStatic)
        for index in range(count):
            x = rng.uniform(-220, 220)
            y = rng.uniform(-70, 760)
            z = rng.uniform(-150, 150)
            vertices.addData3f(x, y, z)
            tint = rng.choices(
                [(0.64, 0.78, 1.0), (1.0, 0.81, 0.59), (0.86, 0.91, 1.0)],
                weights=(0.22, 0.09, 0.69),
            )[0]
            brightness = rng.uniform(0.38, 1.0) if rng.random() < 0.13 else rng.uniform(0.12, 0.48)
            colors.addData4f(*(channel * brightness for channel in tint), 1)
            points.addVertex(index)
        points.closePrimitive()
        geom = Geom(data)
        geom.addPrimitive(points)
        node = GeomNode("deep-field")
        node.addGeom(geom)
        stars = self.render.attachNewNode(node)
        stars.setRenderModeThickness(1.8)
        stars.setLightOff()

        self.nebulae = []
        for position, scale, color in (
            ((-42, 190, 18), (30, 0.15, 17), (0.05, 0.28, 0.48, 0.12)),
            ((35, 285, -22), (25, 0.15, 13), (0.26, 0.12, 0.38, 0.09)),
            ((67, 410, 33), (38, 0.15, 18), (0.42, 0.19, 0.08, 0.075)),
        ):
            cloud = make_sphere(self.render, position, scale, color, "nebula")
            cloud.setTransparency(1)
            self.nebulae.append(cloud)

    def _make_black_hole(self):
        self.hole_position = Vec3(0, 82, 0)
        hole = self.render.attachNewNode("singularity")
        hole.setPos(self.hole_position)
        make_sphere(hole, (0, 0, 0), 3.55, (0.001, 0.002, 0.006, 1), "event-horizon")
        make_sphere(hole, (0, 0, 0), 3.66, (0.003, 0.008, 0.015, 1), "shadow")

        add_ring(hole, (0, 0.12, 0), 3.92, (0.92, 0.91, 0.78, 1), 2.2)
        add_ring(hole, (0, 0.17, 0), 4.08, (0.15, 0.68, 0.92, 0.8), 1.1)
        add_ring(hole, (0, 0.22, 0), 4.3, (0.82, 0.47, 0.19, 0.75), 1.0)

        disk = hole.attachNewNode("accretion-disc")
        for radius, color, width in (
            (5.0, (1.0, 0.44, 0.13, 1), 2.1),
            (5.8, (1.0, 0.76, 0.35, 0.9), 1.6),
            (6.8, (0.34, 0.72, 1.0, 0.9), 1.4),
            (8.0, (0.12, 0.42, 0.88, 0.72), 1.1),
            (9.5, (0.14, 0.27, 0.61, 0.52), 0.9),
        ):
            add_ring(disk, (0, 0, 0), radius, color, width, 180)
        self.disk = disk

        rng = random.Random(91)
        particle_count = 2600
        data = GeomVertexData("plasma-stream", GeomVertexFormat.getV3c4(), Geom.UHStatic)
        data.setNumRows(particle_count)
        vertices = GeomVertexWriter(data, "vertex")
        colors = GeomVertexWriter(data, "color")
        points = GeomPoints(Geom.UHStatic)
        self.plasma = []
        for index in range(particle_count):
            radius = rng.uniform(4.0, 11.5)
            angle = rng.uniform(0, math.tau)
            height = rng.gauss(0, 0.11 + 0.018 * radius)
            vertices.addData3f(radius * math.cos(angle), height, radius * math.sin(angle))
            warmth = max(0.0, 1.0 - (radius - 4.0) / 8.5)
            colors.addData4f(0.24 + 0.76 * warmth, 0.33 + 0.43 * warmth, 0.62 - 0.34 * warmth, rng.uniform(0.35, 1.0))
            points.addVertex(index)
            self.plasma.append((radius, angle, height, rng.uniform(0.25, 1.0)))
        points.closePrimitive()
        geom = Geom(data)
        geom.addPrimitive(points)
        node = GeomNode("infalling-plasma")
        node.addGeom(geom)
        self.plasma_node = disk.attachNewNode(node)
        self.plasma_node.setRenderModeThickness(2.2)
        self.plasma_node.setLightOff()

        self.lens_rays = []
        for index in range(16):
            angle = math.tau * index / 16
            start = Vec3(15 * math.cos(angle), 0.1, 15 * math.sin(angle))
            end = Vec3(4.1 * math.cos(angle + 0.12), 0.1, 4.1 * math.sin(angle + 0.12))
            lines = LineSegs()
            lines.setThickness(0.65)
            lines.setColor(0.3, 0.65, 1.0, 0.34)
            lines.moveTo(start)
            lines.drawTo(end)
            ray = hole.attachNewNode(lines.create())
            ray.setLightOff()
            self.lens_rays.append(ray)

    def _make_tesseract(self):
        self.tesseract_center = Vec3(0, 158, 0)
        self.tesseract_root = self.render.attachNewNode("four-dimensional-projection")
        self.tesseract_root.setPos(self.tesseract_center)

        vertices_4d = list(product((-1.0, 1.0), repeat=4))
        self.vertices_4d = np.asarray(vertices_4d, dtype=float)
        self.edges_4d = [
            (first, second)
            for first in range(16)
            for second in range(first + 1, 16)
            if sum(a != b for a, b in zip(vertices_4d[first], vertices_4d[second])) == 1
        ]

        data = GeomVertexData("tesseract-32-edges", GeomVertexFormat.getV3c4(), Geom.UHDynamic)
        data.setNumRows(len(self.edges_4d) * 2)
        self.tesseract_data = data
        self.tesseract_vertex_writer = GeomVertexWriter(data, "vertex")
        color_writer = GeomVertexWriter(data, "color")
        primitive = GeomLines(Geom.UHDynamic)
        self.edge_colors = []
        for edge_index, (first, second) in enumerate(self.edges_4d):
            differing_axis = next(axis for axis in range(4) if vertices_4d[first][axis] != vertices_4d[second][axis])
            tint = (
                (0.23, 0.83, 1.0, 0.95),
                (0.18, 0.59, 0.92, 0.9),
                (0.45, 0.86, 1.0, 0.93),
                (0.91, 0.67, 0.35, 0.96),
            )[differing_axis]
            self.edge_colors.append(tint)
            for _ in range(2):
                color_writer.addData4f(*tint)
            primitive.addVertices(edge_index * 2, edge_index * 2 + 1)
        primitive.closePrimitive()
        geom = Geom(data)
        geom.addPrimitive(primitive)
        node = GeomNode("32-dimensional-edges")
        node.addGeom(geom)
        edge_path = self.tesseract_root.attachNewNode(node)
        edge_path.setRenderModeThickness(2.2)
        edge_path.setLightOff()

        self.vertex_nodes = []
        for index in range(16):
            tint = (0.35, 0.88, 1.0, 1) if self.vertices_4d[index][3] > 0 else (1.0, 0.68, 0.35, 1)
            marker = make_sphere(self.tesseract_root, (0, 0, 0), 0.095, tint, f"vertex-{index:02d}")
            self.vertex_nodes.append(marker)

        self._update_tesseract(0.0)

    def _make_architecture(self):
        lines = LineSegs("temporal-bookshelves")
        lines.setThickness(1.1)
        for layer in range(12):
            y = 31 + layer * 13.5
            half_width = 15 + layer * 2.1
            half_height = 9 + layer * 1.15
            fade = max(0.14, 0.82 - layer * 0.047)
            tint = (0.12 + 0.12 * (layer % 3 == 0), 0.54 + 0.14 * (layer % 2), 0.77, fade)
            lines.setColor(*tint)
            lines.moveTo(-half_width, y, -half_height)
            lines.drawTo(half_width, y, -half_height)
            lines.drawTo(half_width, y, half_height)
            lines.drawTo(-half_width, y, half_height)
            lines.drawTo(-half_width, y, -half_height)
            shelf_count = 5
            for shelf in range(1, shelf_count + 1):
                z = -half_height + (2 * half_height * shelf / (shelf_count + 1))
                lines.moveTo(-half_width, y, z)
                lines.drawTo(half_width, y, z)
            for divider in range(-2, 3):
                x = half_width * divider / 3
                lines.moveTo(x, y, -half_height)
                lines.drawTo(x, y, half_height)

        for side in (-1, 1):
            for shelf in range(14):
                x = side * (13 + shelf * 1.9)
                lines.setColor(0.22, 0.59, 0.78, max(0.1, 0.65 - shelf * 0.035))
                lines.moveTo(x, 25, -12)
                lines.drawTo(x, 225, -12)
                lines.moveTo(x, 25, 12)
                lines.drawTo(x, 225, 12)
                for y in range(32, 225, 16):
                    lines.moveTo(x, y, -12)
                    lines.drawTo(x, y, 12)

        self.architecture = self.render.attachNewNode(lines.create())
        self.architecture.setLightOff()
        self.architecture.setTransparency(1)
        self.architecture.hide()

        self.time_layers = []
        for index in range(7):
            marker = add_ring(
                self.render,
                (0, 142 + index * 6.0, 0),
                7.5 + index * 2.2,
                (0.19, 0.72, 0.96, max(0.16, 0.54 - index * 0.045)),
                0.9,
                160,
            )
            marker.hide()
            self.time_layers.append(marker)

    def _make_hud(self):
        self.title = OnscreenText(
            text="T E S S E R A C T",
            pos=(-1.28, 0.91),
            scale=0.042,
            fg=(0.78, 0.9, 1.0, 0.88),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.chapter = OnscreenText(
            text=self.phase,
            pos=(-1.28, 0.83),
            scale=0.024,
            fg=(0.44, 0.69, 0.86, 0.78),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.controls_text = OnscreenText(
            text="WASD MOVE     Q / E ALTITUDE     MOUSE LOOK     SHIFT BOOST     M SOUND     H HUD     F11 FULLSCREEN",
            pos=(0, -0.94),
            scale=0.019,
            fg=(0.64, 0.75, 0.86, 0.65),
            align=TextNode.ACenter,
        )
        self.crossing = OnscreenText(
            text="",
            pos=(0, 0.08),
            scale=0.048,
            fg=(0.88, 0.94, 1.0, 0),
            align=TextNode.ACenter,
            mayChange=True,
        )
        card = CardMaker("crossing-flash")
        card.setFrameFullscreenQuad()
        self.flash = self.render2d.attachNewNode(card.generate())
        self.flash.setColor(0.3, 0.58, 0.86, 0)
        self.flash.setTransparency(1)
        self.flash.setBin("fixed", 100)
        self.flash.setDepthWrite(False)

    def _make_audio(self):
        sample_rate = 22050
        duration = 12
        times = np.arange(sample_rate * duration, dtype=np.float32) / sample_rate
        modulation = np.sin(math.tau * 0.075 * times)
        left = (
            0.22 * np.sin(math.tau * 42.0 * times)
            + 0.12 * np.sin(math.tau * (55.0 + 1.8 * modulation) * times + 0.4)
            + 0.055 * np.sin(math.tau * 86.0 * times + 0.9)
        )
        right = (
            0.22 * np.sin(math.tau * 42.4 * times + 0.1)
            + 0.12 * np.sin(math.tau * (54.0 + 1.6 * modulation) * times + 0.7)
            + 0.055 * np.sin(math.tau * 87.0 * times + 0.4)
        )
        envelope = 0.62 + 0.38 * (0.5 + 0.5 * modulation)
        stereo = np.column_stack((left * envelope, right * envelope))
        samples = np.asarray(np.clip(stereo * 32767, -32768, 32767), dtype="<i2")
        with tempfile.NamedTemporaryFile(suffix=".wav") as audio_file:
            with wave.open(audio_file.name, "wb") as writer:
                writer.setnchannels(2)
                writer.setsampwidth(2)
                writer.setframerate(sample_rate)
                writer.writeframes(samples.tobytes())
            self.ambience = self.loader.loadSfx(audio_file.name)
        self.sound_enabled = self.ambience is not None
        if self.ambience:
            self.ambience.setLoop(True)
            self.ambience.setVolume(0.2)
            self.ambience.play()

    def _bind_controls(self):
        for key in ("w", "a", "s", "d", "q", "e", "shift"):
            self.accept(key, self.keys.add, [key])
            self.accept(f"{key}-up", self.keys.discard, [key])
        self.accept("f11", self.toggle_fullscreen)
        self.accept("h", self.toggle_hud)
        self.accept("m", self.toggle_sound)
        self.accept("escape", self.userExit)
        self.accept("tab", self.toggle_mouse_capture)

    def _set_mouse_capture(self, enabled):
        self.mouse_captured = enabled
        properties = WindowProperties()
        properties.setCursorHidden(enabled)
        self.win.requestProperties(properties)
        if enabled and self.win:
            self.win.movePointer(0, self.win.getXSize() // 2, self.win.getYSize() // 2)

    def toggle_mouse_capture(self):
        self._set_mouse_capture(not self.mouse_captured)

    def toggle_fullscreen(self):
        properties = WindowProperties()
        properties.setFullscreen(not self.win.getProperties().getFullscreen())
        self.win.requestProperties(properties)

    def toggle_hud(self):
        self.hud_visible = not self.hud_visible
        for item in (self.title, self.chapter, self.controls_text):
            item.show() if self.hud_visible else item.hide()

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        if self.ambience:
            self.ambience.setVolume(0.2 if self.sound_enabled else 0.0)

    def _rotate_4d(self, time_value):
        matrix = np.eye(4)
        for (first_axis, second_axis), rate in PLANE_RATES.items():
            angle = time_value * rate
            cosine, sine = math.cos(angle), math.sin(angle)
            rotation = np.eye(4)
            rotation[first_axis, first_axis] = cosine
            rotation[second_axis, second_axis] = cosine
            rotation[first_axis, second_axis] = -sine
            rotation[second_axis, first_axis] = sine
            matrix = rotation @ matrix
        return matrix

    def _project_4d(self, time_value):
        transformed = self.vertices_4d @ self._rotate_4d(time_value).T
        denominator = 3.6 - transformed[:, 3]
        perspective = 3.1 / np.maximum(0.55, denominator)
        return transformed[:, :3] * perspective[:, None] * 5.7

    def _update_tesseract(self, time_value):
        projected = self._project_4d(time_value)
        for edge_index, (first, second) in enumerate(self.edges_4d):
            self.tesseract_vertex_writer.setRow(edge_index * 2)
            self.tesseract_vertex_writer.setData3f(*projected[first])
            self.tesseract_vertex_writer.setRow(edge_index * 2 + 1)
            self.tesseract_vertex_writer.setData3f(*projected[second])
        self.tesseract_data.setNumRows(len(self.edges_4d) * 2)
        for marker, position in zip(self.vertex_nodes, projected):
            marker.setPos(*position)

    def _begin_crossing(self):
        self.phase = "TRANSIT  /  EVENT HORIZON"
        self.phase_time = 0.0
        self.chapter.setText(self.phase)
        self.crossing.setText("THE LIGHT DOES NOT ESCAPE")
        if self.ambience and self.sound_enabled:
            self.ambience.setPlayRate(0.72)
            self.ambience.setVolume(0.32)
        self._set_mouse_capture(False)

    def _finish_crossing(self):
        self.phase = "ARRIVAL  /  THE FIFTH DIMENSION"
        self.chapter.setText(self.phase)
        self.crossing.setText("TIME IS A PLACE")
        self.camera.setPos(0, 119, 0)
        self.camera.setHpr(0, 0, 0)
        self.architecture.show()
        for marker in self.time_layers:
            marker.show()
        self.phase_time = 0.0
        if self.ambience:
            self.ambience.setPlayRate(1.0)
            self.ambience.setVolume(0.2 if self.sound_enabled else 0.0)
        self._set_mouse_capture(True)

    def _read_mouse(self, dt):
        if not self.mouse_captured or not self.win:
            return
        center_x = self.win.getXSize() // 2
        center_y = self.win.getYSize() // 2
        pointer = self.win.getPointer(0)
        delta_x, delta_y = pointer.getX() - center_x, pointer.getY() - center_y
        if abs(delta_x) + abs(delta_y) > 0:
            self.camera.setH(self.camera.getH() - delta_x * 0.11)
            self.camera.setP(max(-82, min(82, self.camera.getP() + delta_y * 0.1)))
            self.win.movePointer(0, center_x, center_y)

    def _move_camera(self, dt):
        if self.phase.startswith("TRANSIT"):
            return
        position = self.camera.getPos()
        if self.phase.startswith("VOYAGE"):
            position.y += dt * 1.15
        speed = 5.2 * (3.4 if "shift" in self.keys else 1.0)
        heading = math.radians(self.camera.getH())
        forward = Vec3(-math.sin(heading), math.cos(heading), 0)
        right = Vec3(math.cos(heading), math.sin(heading), 0)
        if "w" in self.keys:
            position += forward * speed * dt
        if "s" in self.keys:
            position -= forward * speed * dt
        if "a" in self.keys:
            position -= right * speed * dt
        if "d" in self.keys:
            position += right * speed * dt
        if "q" in self.keys:
            position.z -= speed * dt
        if "e" in self.keys:
            position.z += speed * dt
        self.camera.setPos(position)

    def update(self, task):
        dt = min(ClockObject.getGlobalClock().getDt(), 0.04)
        self.total_time += dt
        self.phase_time += dt
        self._read_mouse(dt)

        self.disk.setR(self.total_time * 34)
        for index, ray in enumerate(self.lens_rays):
            ray.setColorScale(1, 1, 1, 0.65 + 0.28 * math.sin(self.total_time * 1.8 + index))
        if not self.phase.startswith("TRANSIT"):
            self._move_camera(dt)

        hole_distance = (self.camera.getPos() - self.hole_position).length()
        if self.phase.startswith("VOYAGE"):
            approach = max(0.0, min(1.0, (42.0 - hole_distance) / 42.0))
            self.camLens.setFov(76 + 11 * approach)
        if self.phase.startswith("VOYAGE") and hole_distance < 4.8:
            self._begin_crossing()
        if self.phase.startswith("TRANSIT"):
            pulse = max(0.0, math.sin(self.phase_time * 14)) ** 14
            self.flash.setColor(0.32, 0.7, 1.0, pulse * 0.27)
            self.camera.setH(self.camera.getH() + math.sin(self.phase_time * 37) * dt * 4.2)
            self.crossing.setFg((0.88, 0.94, 1.0, min(1.0, self.phase_time * 0.7)))
            if self.phase_time > 3.8:
                self._finish_crossing()
        else:
            self.flash.setColor(0.3, 0.58, 0.86, 0)

        if self.phase.startswith("ARRIVAL"):
            self._update_tesseract(self.total_time)
            self.crossing.setFg((0.88, 0.94, 1.0, max(0.0, 1.0 - max(0, self.phase_time - 2.2) * 0.22)))
            self.camera.setPos(self.camera.getPos() + Vec3(0, 0.18 * dt, 0))
        return Task.cont


if __name__ == "__main__":
    TesseractJourney().run()