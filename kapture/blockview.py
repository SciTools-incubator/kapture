import argparse
import collections
import itertools
import linecache

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import matplotlib.patheffects as PathEffects
import numpy as np


LOG_PATH = 'log.txt'


def parse_code(log, nlines=10):
    """Pull out code snippet from whatever file"""
    code = []
    #iterate through each entry
    for entry in log:
        tmp = []
        if entry.line_no:
            #parse the code surrounding the line
            lines = np.arange(entry.line_no-(nlines//2),
                              entry.line_no+(nlines//2))
            for line in lines:
                readline = linecache.getline(entry.path, line)
                if readline:
                    if line == entry.line_no:
                        tmp.append("%s > %s" % (line, readline))
                    else:
                        tmp.append("%s   %s" % (line, readline))

            code.append(tmp)
            linecache.clearcache()

    return code


def read_log(log_path):
    my_locals = {}
    execfile(log_path, globals(), my_locals)
    return my_locals['log']


_Frame = collections.namedtuple('_Frame', ('path', 'line_no', 'func_name',
                                           'line', 'module'))


class CallDiagram(object):
    class _MouseEvent(object):
        pass

    def __init__(self, log):
        self.log = log
        self.packages = []
        self.active_patches = []

    def _package(self, frame):
        return (frame.module or "").split('.')[0]

    def _package_colours(self):
        packages = set()
        for stack in self.log:
            for frame in stack:
                packages.add(self._package(frame))
        package_colours = dict(zip(packages, itertools.cycle('bgrcmy')))
        return package_colours

    def _format_coord(self, xdata, ydata):
        event = CallDiagram._MouseEvent()
        axes = plt.gca()
        xy = axes.transData.transform(((xdata, ydata),))
        event.x = xy[0][0]
        event.y = xy[0][1]
        event.xdata = xdata
        event.ydata = ydata
        patch = self._find_patch(event)
        label = self._label([patch] if patch else [])
        return label

    def _find_patch(self, event):
        for patch in self._axes.patches:
            inside, details = patch.contains(event)
            if inside:
                return patch
        return None

    def _find_matching_patches(self, event):
        patch_hit = None
        for patch in self._axes.patches:
            inside, details = patch.contains(event)
            if inside:
                patch_hit = patch
                break
        if not patch_hit or not hasattr(patch, 'frame'):
            return []
        # Else return all matching patchs
        match_frame = patch_hit.frame
        return [patch for patch in self._axes.patches
                if hasattr(patch, 'frame') and patch.frame == match_frame]

    def _label(self, all_patches):
        label = ''
        if all_patches:
            frame = all_patches[0].frame
            if frame.path == '<string>':
                module = frame.path
                location = frame.func_name
            else:
                module = frame.module
                location = frame.line_no
            total_flow = sum(patch.flow for patch in all_patches)
            flow_percentage = 100.0 * total_flow / len(self.log)
            label = '{}: {} ({:.1f}%)'.format(module, location,
                                              flow_percentage)
        return label

    def _onclick(self, event, debug=False):
        if debug:
            print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f' % (
                event.button, event.x, event.y, event.xdata, event.ydata)

        #pop-up style
        props = dict(boxstyle='square', facecolor='white')

        #remove previous text box
        if self._axes.texts:
            del self._axes.texts[-1]

        for patch in self.active_patches:
            patch.set_path_effects([])
            patch.set_zorder(1)

        #if within patch display textbox on mouse click
        self.active_patches = self._find_matching_patches(event)
        label = self._label(self.active_patches)
        for patch in self.active_patches:
            code = parse_code([patch.frame])[0] or '<string>'
            patch.set_path_effects([PathEffects.withStroke(
                linewidth=3, foreground="yellow")])
            patch.set_zorder(2)

        #plot code text box if there is a valid code snippet
        if label and code:
            x, y = event.xdata, event.ydata
            inset = 10
            x = inset
            y = plt.gcf().get_figheight() * plt.gcf().get_dpi() - inset
            #import pdb; pdb.set_trace()
            plt.text(x, y,
                     label + '\n' + ''.join(code),
                     ha='left', fontsize=10,
                     bbox=props, verticalalignment='top',
                     #transform=plt.gcf().transFigure,
                     zorder=3,
                     transform=None,
                     family='monospace')
        plt.draw()

    def _sub_branches(self, branch):
        # Group the sub-branches by frame
        sub_branches_by_frame = {}
        for stack in branch:
            if len(stack) > 1:
                sub_frame = stack[1]
                sub_branch = sub_branches_by_frame.setdefault(sub_frame, [])
                sub_branch.append(stack[1:])
        sub_branches = sub_branches_by_frame.values()
        return sub_branches

    def _add_block(self, ax, branch, top_left_x, top_right_x, top_y, bottom_x):
        flow = len(branch)
        half_width = self.fraction * flow / 2.0
        bottom_y = top_y - 10
        bottom_left_x = bottom_x - half_width
        bottom_right_x = bottom_x + half_width
        frame = branch[0][0]
        colour = self.package_colours.get(self._package(frame), 'k')
        alpha = 1 if len(branch) > 1 else 0.3
        patch = Polygon([(top_left_x, top_y),
                         (top_right_x, top_y),
                         (bottom_right_x, bottom_y),
                         (bottom_right_x, bottom_y - 10),
                         (bottom_left_x, bottom_y - 10),
                         (bottom_left_x, bottom_y)],
                        facecolor=colour, alpha=alpha)
        patch.frame = frame
        patch.flow = len(branch)
        ax.add_patch(patch)

        sub_branches = self._sub_branches(branch)
        mid_flow = 0.0
        previous_half_flow = 0.0
        for sub_branch in sub_branches:
            if all(len(stack) == 0 for stack in sub_branch):
                raise RuntimeError()
                continue
            half_flow = len(sub_branch) / 2.0
            mid_flow += previous_half_flow + half_flow
            previous_half_flow = half_flow
            sub_top_left_x = (bottom_left_x + 2 * half_width *
                              (mid_flow - half_flow) / flow)
            sub_top_right_x = (bottom_left_x + 2 * half_width *
                               (mid_flow + half_flow) / flow)
            sub_bottom_x = bottom_x - flow / 2.0 + mid_flow
            self._add_block(ax, sub_branch, sub_top_left_x, sub_top_right_x,
                            bottom_y - 10, sub_bottom_x)

    def render(self, log_file_name):
        self.package_colours = self._package_colours()
        fig = plt.figure()
        ax = self._axes = fig.add_subplot(1, 1, 1, xticks=[], yticks=[])
        t = ax.set_title(log_file_name)
        t.set_y(1.01)

        self.fraction = 0.95
        half_width = self.fraction * len(self.log) / 2.
        self._add_block(ax, self.log, -half_width, half_width, 0, 0)
        ax.autoscale(True)
        ax.format_coord = self._format_coord
        fig.canvas.mpl_connect('button_press_event', self._onclick)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='view traceback logs')
    parser.add_argument('-l', '--log', default=LOG_PATH)
    args = parser.parse_args()
    log_file_name = args.log
    log = read_log(log_file_name)

    diagram = CallDiagram(log)
    diagram.render(log_file_name)

    plt.show()
