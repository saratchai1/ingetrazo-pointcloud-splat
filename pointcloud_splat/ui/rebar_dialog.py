# SPDX-License-Identifier: GPL-3.0-or-later
"""Review an isolated ROI; no document mutation until accepted-bar creation."""
from copy import deepcopy
import json
import numpy as np
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox, QDoubleSpinBox,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QVector3D
from ..rebar import inspect, commit_review, spacing


class RebarDialog(QDialog):
    def __init__(self, manager):
        super().__init__(manager)
        self.manager = manager
        self.dataset = manager.datasets[manager._active_idx]
        self.report = None
        self.analysis_version = None
        if hasattr(manager.app, 'add_overlay'):
            import weakref
            reference = weakref.ref(self)
            def preview(viewport, painter):
                dialog = reference()
                if dialog is not None and dialog.isVisible():
                    dialog.draw_preview(viewport, painter)
            manager.app.add_overlay(preview)
        self.setWindowTitle('Rebar Inspection — assisted single layer')
        self.resize(1050, 600)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Enable a section box around ONE layer and parallel family. Coordinates and spacing are metres.\n'
                               'Diameter is design input. Partial scans can bias centres. Confidence is a quality heuristic.'))
        self.direction = QComboBox(); self.direction.addItems(['X', 'Y', 'Z'])
        self.direction.setEditable(True)
        self.direction.setToolTip('X, Y, Z or approximate world direction x,y,z (e.g. 1,1,0)')
        layout.addWidget(self.direction)
        self.diameter = QDoubleSpinBox(); self.diameter.setRange(3, 100); self.diameter.setValue(16)
        self.diameter.setSuffix(' mm (design diameter)'); layout.addWidget(self.diameter)
        detect = QPushButton('Analyze section box'); detect.clicked.connect(self.analyze); layout.addWidget(detect)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(['Accept', 'X1 m', 'Y1 m', 'Z1 m', 'X2 m', 'Y2 m', 'Z2 m', 'Support / residual', 'Quality'])
        layout.addWidget(self.table)
        self.table.itemChanged.connect(lambda _: self.manager.app.viewport.update()
                                       if hasattr(self.manager.app.viewport, 'update') else None)
        self.evidence = QLabel('No analysis yet'); self.evidence.setWordWrap(True); layout.addWidget(self.evidence)
        export = QPushButton('Export reviewed evidence JSON'); export.clicked.connect(self.export); layout.addWidget(export)
        create = QPushButton('Create accepted native bars (one Undo step)'); create.clicked.connect(self.create); layout.addWidget(create)

    def analyze(self):
        try:
            m = self.manager
            if not m.chk_clipping.isChecked():
                raise ValueError('Enable the section box first')
            low = [m.spin_x_min.value(), m.spin_y_min.value(), m.spin_z_min.value()]
            high = [m.spin_x_max.value(), m.spin_y_max.value(), m.spin_z_max.value()]
            text = self.direction.currentText().strip().upper()
            direction = {'X':[1,0,0], 'Y':[0,1,0], 'Z':[0,0,1]}.get(text)
            if direction is None:
                direction = [float(x) for x in text.split(',')]
            self.report = inspect(self.dataset, low, high, direction, self.diameter.value()/1000,
                                  viewport=m.app.viewport)
            self.analysis_version = m.app.viewport.scene.version
            self.transform_sample = self.dataset.apply_transform(np.vstack((np.zeros(3), np.eye(3))), m.app.viewport).copy()
            self.table.setRowCount(len(self.report['bars']))
            for row, bar in enumerate(self.report['bars']):
                accept = QTableWidgetItem(); accept.setCheckState(Qt.Unchecked); self.table.setItem(row, 0, accept)
                for col, value in enumerate(bar['start']+bar['end'], 1):
                    self.table.setItem(row, col, QTableWidgetItem(f'{value:.9f}'))
                e = bar['evidence']
                for col, text in [(7, f"{e['support']} / {e['residual_p95_m']*1000:.2f} mm"),
                                  (8, f"{e['confidence_heuristic']:.2f}")]:
                    item = QTableWidgetItem(text); item.setFlags(item.flags() & ~Qt.ItemIsEditable); self.table.setItem(row, col, item)
            self.update_spacing(self.report)
        except Exception as exc:
            self.report = None
            self.table.setRowCount(0)
            QMessageBox.warning(self, 'Analysis unavailable', str(exc))

    def reviewed(self):
        if self.report is None:
            raise ValueError('Analyze a section box first')
        report = deepcopy(self.report)
        for row, bar in enumerate(report['bars']):
            values = [float(self.table.item(row, c).text()) for c in range(1, 7)]
            if not np.isfinite(values).all():
                raise ValueError('Endpoints must be finite')
            bar['detected_start'], bar['detected_end'] = bar['start'], bar['end']
            bar['start'], bar['end'] = values[:3], values[3:]
            bar['review_adjusted'] = not np.allclose(values, bar['detected_start']+bar['detected_end'], atol=1e-8, rtol=0)
            bar['evidence_basis'] = 'detected_endpoints_before_manual_review'
            bar['accepted'] = self.table.item(row, 0).checkState() == Qt.Checked
        report['spacing'] = spacing(report['bars'], report['direction'])
        self.update_spacing(report)
        return report

    def update_spacing(self, report):
        removed = report.get('background_filter', {}).get('removed_points', 0)
        self.evidence.setText(f'Surface points excluded: {removed:,}. Centreline spacing: '+('; '.join(f"{s['bars'][0]+1}–{s['bars'][1]+1}: {s['centreline_m']*1000:.2f} mm" for s in report['spacing']) or 'No overlapping pairs'))

    def create(self):
        try:
            m = self.manager
            if self.report is None:
                raise ValueError('Analyze a section box first')
            if m.app.viewport.scene.version != self.analysis_version:
                raise ValueError('Document changed since analysis; analyze again')
            if self.dataset not in m.datasets:
                raise ValueError('Dataset is no longer loaded')
            # Reject stale scan transforms after analysis, rather than create misplaced bars.
            current = self.dataset.apply_transform(np.vstack((np.zeros(3), np.eye(3))), m.app.viewport)
            if not np.allclose(current, self.transform_sample, atol=1e-7, rtol=0):
                raise ValueError('Dataset moved since analysis; analyze again')
            commit_review(m.app.viewport.history, self.reviewed())
            m.app.viewport.notify_scene_changed()
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, 'Cannot create bars', str(exc))

    def draw_preview(self, viewport, painter):
        if self.report is None or viewport.scene.version != self.analysis_version:
            return
        for row in range(self.table.rowCount()):
            try:
                values = [float(self.table.item(row, col).text()) for col in range(1, 7)]
                a = viewport._world_to_pixel(QVector3D(*values[:3]))
                b = viewport._world_to_pixel(QVector3D(*values[3:]))
                if a is None or b is None:
                    continue
                accepted = self.table.item(row, 0).checkState() == Qt.Checked
                painter.setPen(QPen(QColor('#32d583' if accepted else '#ffb547'), 2))
                painter.drawLine(QPointF(*a), QPointF(*b))
                painter.drawText(QPointF(*a), str(row+1))
            except (ValueError, TypeError, AttributeError):
                continue

    def export(self):
        try:
            report = self.reviewed()
            path, _ = QFileDialog.getSaveFileName(self, 'Evidence', 'rebar-evidence.json', 'JSON (*.json)')
            if path:
                from pathlib import Path
                Path(path).write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        except Exception as exc:
            QMessageBox.warning(self, 'Cannot export', str(exc))
