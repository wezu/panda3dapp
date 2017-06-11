""" This is a replacement for ShowBase for starting a Panda3D application.
It opens a window, starts the task, interval, messenge, and event managers,
garbage collector task, and creates a camera and scengraph for 3D and 2D.
It uses DirectObject like interface, only in snake_case (eg. ignore_all() not ignoreAll())

It will NOT:
-put things into buildins
-use NodePath-extensions
-setup sound system
-setup collision traversers
-setup camera controll
-setup wx or tk
-setup particle system
-setup physics
-setup BulletinBoard
-setup Jobs
-create render2dp, aspect2dp and any aspect2d children (a2dTop, a2dBottomCenterNs, etc)
-enforce a singelton pattern (shoot your own foot if you like)
-walk the dog, put out the trash
"""

__all__ = ['PandaApp']

from panda3d.core import *
from panda3d.direct import throw_new_frame
from panda3d.direct import storeAccessibilityShortcutKeys
from panda3d.direct import allowAccessibilityShortcutKeys

from direct.showbase.EventManagerGlobal import eventMgr
from direct.showbase.MessengerGlobal import messenger
from direct.task.TaskManagerGlobal import taskMgr
from direct.task import Task
from direct.interval import IntervalManager
from direct.showbase import Loader
from direct.showbase import AppRunnerGlobal

from simpleconfig import SimpleConfig as Config

try:
    from functools import lru_cache
except ImportError:
    from lru_backport import lru_cache
import time
import os

class PandaApp(object):

    def __init__(self):
        # This contains the global appRunner instance, as imported from
        # AppRunnerGlobal.  This will be None if we are not running in the
        # runtime environment (ie. from a .p3d file).
        self.app_runner = AppRunnerGlobal.appRunner

        #store the Config class, it's nice, use it
        self.config=Config

        #Set the default loader... for some reason
        self.graphics_engine = GraphicsEngine.get_global_ptr()
        self.loader = Loader.Loader(self)

        # This is the DataGraph traverser, which we might as well
        # create now.
        self.data_graph_trav = DataGraphTraverser()
        self.data_root = NodePath('data_root')
        self.data_root_node = self.data_root.node()

        #Disable sticky keys
        if Config['disable-sticky-keys']:
            storeAccessibilityShortcutKeys()
            allowAccessibilityShortcutKeys(False)

        #Make render, render2d and pixel2d nodes
        self.render = NodePath('render')
        self.render2d = NodePath('render2d')
        self.render2d.set_depth_test(0)
        self.render2d.set_depth_write(0)
        self.render2d.set_material_off(1)
        self.render2d.set_two_sided(1)
        self.aspect2d = self.render2d.attach_new_node(PGTop("aspect2d"))
        aspectRatio = self.get_aspect_ratio()
        self.aspect2d.set_scale(1.0 / aspectRatio, 1.0, 1.0)
        self.pixel2d = self.render2d.attach_new_node(PGTop("pixel2d"))
        self.pixel2d.set_pos(-1, 0, 1)
        xsize, ysize = self.get_size()
        if xsize > 0 and ysize > 0:
            self.pixel2d.set_scale(2.0 / xsize, 1.0, 2.0 / ysize)

        #Open default window
        self._open_main_window()

        # The global event manager, as imported from EventManagerGlobal.
        self.event_mgr = eventMgr
        # The global messenger, as  imported from MessengerGlobal.
        self.messenger = messenger
        # The global task manager, as imported from TaskManagerGlobal.
        self.task_mgr = taskMgr

        # Get a pointer to Panda's global ClockObject, used for
        # synchronizing events between Python and C.
        self.global_clock = ClockObject.getGlobalClock()

        #Make sure the globalClock object is in sync with the TrueClock.
        self.global_clock.setRealTime(TrueClock.getGlobalPtr().getShortTime())
        self.global_clock.tick()

        #Make the TaskManager start using the new globalClock.
        self.task_mgr.globalClock = self.global_clock

        #Listen for window shape, size and focus change events
        self.accept('window-event', self._on_window_event)

        # Start render_frame_loop
        self.restart()

    def _get_win_props(self):
        if getattr(self, 'win', None):
            props=self.win.get_requested_properties()
            if props.has_size(): #no size? probably not what we want.
                return props
            else:
                props=self.win.get_properties()
            if props.has_size():
                return props
        return WindowProperties.get_default()

    def _open_main_window(self):
        """
        Creates the initial, main window for the application, and sets
        up the mouse and render2d structures appropriately for it.
        """
        if not getattr(self, 'pipe', None):
            self.pipe = GraphicsPipeSelection.get_global_ptr().make_default_pipe()

        # Open a new window.
        flags = GraphicsPipe.BF_require_window | GraphicsPipe.BF_fb_props_optional
        fbprops = FrameBufferProperties.get_default()
        props = WindowProperties.get_default()
        props = WindowProperties(props)
        props.set_size(*Config['win-size'])

        self.win = self.graphics_engine.make_output(self.pipe, 'main_window', 0,
                                                    fbprops, props, flags)

        if self.win != None:
            self.minimized=False
            self.focus=False
            self.last_win_size=self.get_size()
            #make a display_region for 2d
            dr = self.win.make_mono_display_region(*(0, 1, 0, 1))
            dr.set_sort(10)
            dr.set_clear_depth_active(1)
            # Make any texture reloads on the gui come up immediately.
            dr.set_incomplete_render(False)

            # make a 2d camera
            cam_2d_node = Camera('cam2d')
            lens = OrthographicLens()
            left, right, bottom, top = (-1, 1, -1, 1)
            lens.set_film_size(right - left, top - bottom)
            lens.set_film_offset((right + left) * 0.5, (top + bottom) * 0.5)
            lens.set_near_far(-1000, 1000)
            cam_2d_node.set_lens(lens)
            self.camera2d = self.render2d.attach_new_node('camera2d')
            camera2d = self.camera2d.attach_new_node(cam_2d_node)
            dr.set_camera(camera2d)
            self.cam2d = camera2d

            #make the default camera and display_region
            self.camera = self.render.attach_new_node(ModelNode('camera'))
            self.camera.node().set_preserve_transform(ModelNode.PTLocal)
            # Make a  Camera node.
            cam_node = Camera('cam')
            self.lens = PerspectiveLens()
            self.lens.set_aspect_ratio(self.get_aspect_ratio())
            cam_node.set_lens(self.lens)
            self.cam = self.camera.attach_new_node(cam_node)
            dr = self.win.make_display_region(*(0, 1, 0, 1))
            dr.set_sort(0)
            dr.set_camera(self.cam)

            #setup mouse and keyboard inputs
            self.button_throwers = []
            self.pointer_watcher_nodes = []
            for i in range(self.win.get_num_input_devices()):
                name = self.win.get_input_device_name(i)
                mk = self.data_root.attach_new_node(MouseAndKeyboard(self.win, i, name))
                mw = mk.attach_new_node(MouseWatcher("watcher%s" % (i)))

                if self.win.get_side_by_side_stereo():
                    # If the window has side-by-side stereo enabled, then
                    # we should constrain the MouseWatcher to the window's
                    # DisplayRegion.  This will enable the MouseWatcher to
                    # track the left and right halves of the screen
                    # individually.
                    mw.node().set_display_region(self.win.get_overlay_display_region())

                mb = mw.node().get_modifier_buttons()
                mb.add_button(KeyboardButton.shift())
                mb.add_button(KeyboardButton.control())
                mb.add_button(KeyboardButton.alt())
                mb.add_button(KeyboardButton.meta())
                mw.node().set_modifier_buttons(mb)
                bt = mw.attach_new_node(ButtonThrower("buttons%s" % (i)))
                if (i != 0):
                    bt.node().set_prefix('mousedev%s-' % (i))
                mods = ModifierButtons()
                mods.add_button(KeyboardButton.shift())
                mods.add_button(KeyboardButton.control())
                mods.add_button(KeyboardButton.alt())
                mods.add_button(KeyboardButton.meta())
                bt.node().set_modifier_buttons(mods)
                self.button_throwers.append(bt)
                if (self.win.has_pointer(i)):
                    self.pointer_watcher_nodes.append(mw.node())

            self.mouse_watcher = self.button_throwers[0].get_parent()
            self.mouse_watcher_node = self.mouse_watcher.node()

            # Tell the gui system about our new mouse watcher.
            self.aspect2d.node().set_mouse_watcher(self.mouse_watcher_node)
            self.pixel2d.node().set_mouse_watcher(self.mouse_watcher_node)
            self.mouse_watcher_node.add_region(PGMouseWatcherBackground())

            self.set_frame_rate_meter(Config['show-frame-rate-meter'])
            return True
        return False

    def __reset_prev_transform(self, state):
        """Clear out the previous velocity deltas now, after we have
        rendered (the previous frame).  We do this after the render,
        so that we have a chance to draw a representation of spheres
        along with their velocities.  At the beginning of the frame
        really means after the command prompt, which allows the user
        to interactively query these deltas meaningfully."""
        PandaNode.reset_all_prev_transform()
        return Task.cont

    def __interval_loop(self, state):
        """Execute all intervals in the global ivalMgr."""
        IntervalManager.ivalMgr.step()
        return Task.cont

    def __garbage_collect_states(self, state):
        """ This task is started only when we have
        garbage-collect-states set in the Config.prc file, in which
        case we're responsible for taking out Panda's garbage from
        time to time.  This is not to be confused with Python's
        garbage collection.  """
        TransformState.garbage_collect()
        RenderState.garbage_collect()
        return Task.cont

    def __render_frame_loop(self, state):
        # Render the frame.
        self.graphics_engine.render_frame()

        if self.minimized:
            # If the main window is minimized, slow down the app a bit
            # by sleeping here in igLoop so we don't use all available
            # CPU needlessly.
            time.sleep(0.1)
        # Lerp stuff needs this event, and it must be generated in
        # C++, not in Python.
        throw_new_frame()
        return Task.cont

    def __data_loop(self, state):
        """Traverse the data graph.  This reads all the control
        inputs (from the mouse and keyboard, for instance) """
        self.data_graph_trav.traverse(self.data_root_node)
        return Task.cont

    def _adjust_window_aspect_ratio(self, aspectRatio):
        if getattr(self, 'win', None):
            self.pixel2d.set_scale(2.0 / self.win.get_sbs_left_x_size(), 1.0, 2.0 / self.win.get_sbs_left_y_size())
        if getattr(self, 'lens', None):
            self.lens.set_aspect_ratio(aspectRatio)
        if aspectRatio < 1:
            # If the window is TALL, lets expand the top and bottom
            self.aspect2d.set_scale(1.0, aspectRatio, aspectRatio)
        else:
            # If the window is WIDE, lets expand the left and right
            self.aspect2d.set_scale(1.0 / aspectRatio, 1.0, 1.0)

    def _on_window_event(self, win):
        #fire the event only for our window
        if getattr(self, 'win', None):
            if win != self.win:
                return
        #fire the event only once per frame
        if not getattr(self, 'last_event_frame', None):
            self.last_event_frame=0
        if self.last_event_frame == self.global_clock.get_frame_count():
            return
        self.last_event_frame=self.global_clock.get_frame_count()

        properties = win.get_properties()
        #window resize
        size=tuple(properties.get_size())
        if size != self.last_win_size:
            self._adjust_window_aspect_ratio(self.get_aspect_ratio())
            self.last_win_size=tuple(size)
            self.send('window-event-resize')
        #window is closed
        if not properties.get_open():
            self.send('window-event-close')
            self.exit()
        #window focused
        if properties.get_foreground():
            if not self.focus:
                self.focus=True
                self.send('window-event-focus')
        else:
            self.focus=False
            self.send('window-event-focus-lost')
        #window is (un-)minimized
        if properties.get_minimized():
            if not self.minimized:
                self.minimized=True
                self.send('window-event-minimize')
        elif self.minimized:
            self.minimized=False
            self.send('window-event-restore')

    def set_frame_rate_meter(self, flag):
        """
        Turns on or off (according to flag) a standard frame rate
        meter in the upper-right corner of the main window.
        """
        if flag:
            if not getattr(self, 'frame_rate_meter', None):
                self.frame_rate_meter = FrameRateMeter('frameRateMeter')
                self.frame_rate_meter.setup_window(self.win)
        else:
            if getattr(self, 'frame_rate_meter', None):
                self.frame_rate_meter.clear_window()
                del self.frame_rate_meter

    def exit(self):
        self.send('exit')
        self.destroy()
        os._exit(1)

    def restart(self):
        self.task_mgr.remove('render_frame_loop')
        self.task_mgr.remove('reset_prev_transform')
        self.task_mgr.remove('interval_loop')
        self.task_mgr.remove('data_loop')
        self.task_mgr.remove('garbage_collect_states')
        self.event_mgr.restart()
        # __resetPrevTransform goes at the very beginning of the frame.
        self.task_mgr.add(
            self.__reset_prev_transform, 'reset_prev_transform', sort = -51)
        # give the dataLoop task a reasonably "early" sort,
        # so that it will get run before most tasks
        self.task_mgr.add(self.__data_loop, 'data_loop', sort = -50)
        # spawn the ivalLoop with a later sort, so that it will
        # run after most tasks, but before igLoop.
        self.task_mgr.add(self.__interval_loop, 'interval_loop', sort = 20)

        if Config['garbage-collect-states']:
            self.task_mgr.add(self.__garbage_collect_states, 'garbage_collect_states', sort = 46)
        # give the igLoop task a reasonably "late" sort,
        # so that it will get run after most tasks
        self.task_mgr.add(self.__render_frame_loop, 'render_frame_loop', sort = 50)

    def get_size(self):
        """Returns the actual size of the indicated (or main
        window), or the default size if there is not yet a
        main window."""
        props=self._get_win_props()
        if props.has_size():
            return props.get_x_size(), props.get_y_size()
        return 0, 0

    def get_aspect_ratio(self):
        """Returns the actual aspect ratio of the indicated (or main
        window), or the default aspect ratio if there is not yet a
        main window."""
        aspect_ratio = 1
        props=self._get_win_props()
        if props.has_size() and props.get_y_size() != 0:
            aspect_ratio = float(props.get_x_size()) / float(props.get_y_size())
        if aspect_ratio == 0:
            return 1
        return aspect_ratio

    def destroy(self):
        """ Call this function to destroy the PandaApp and stop all
        its tasks, freeing all of the Panda resources.  Normally, you
        should not need to call it explicitly, as it is bound to the
        exitfunc and will be called at application exit time
        automatically."""

        #Restore sticky key settings
        if Config['disable-sticky-keys']:
            allowAccessibilityShortcutKeys(True)

        self.ignore_all()
        self.task_mgr.remove('render_frame_loop')
        self.task_mgr.remove('reset_prev_transform')
        self.task_mgr.remove('interval_loop')
        self.task_mgr.remove('data_loop')
        self.task_mgr.remove('garbage_collect_states')
        self.event_mgr.shutdown()

        if getattr(self, 'loader', None):
            self.loader.destroy()
            del self.loader
        if getattr(self, 'graphics_engine', None):
            self.graphics_engine.remove_all_windows()

    def run(self):
        """ This method runs the TaskManager when self.appRunner is
        None, which is to say, when we are not running from within a
        p3d file.  When we *are* within a p3d file, the Panda
        runtime has to be responsible for running the main loop, so
        we can't allow the application to do it. """

        if self.app_runner is None or self.app_runner.dummy or \
           (self.app_runner.interactiveConsole and not self.app_runner.initialAppImport):
            self.task_mgr.run()

    #Functions added for convinence
    def load_model(self, *args, **kwargs):
        if 'parent' in kwargs:
            parent=kwargs['parent']
            del kwargs['parent']
            model=self.loader.load_model(*args, **kwargs)
            model.reparent_to(parent)
            return model
        else:
            return self.loader.load_model(*args, **kwargs)

    def load_tex(self, *args, **kwargs):
        return self.loader.load_texture(*args, **kwargs)

    def load_sound(self, *args, **kwargs):
        return self.loader.load_sound(*args, **kwargs)

    def load_font(self, *args, **kwargs):
        return self.loader.load_font(*args, **kwargs)

    def load_shader(self, *args, **kwargs):
        return self.loader.load_shader(*args, **kwargs)

    @lru_cache(maxsize=64)
    def load_glsl_shader(self, v_shader, f_shader, define=None, version='#version 140'):
        # load the shader text
        with open(getModelPath().find_file(v_shader).to_os_specific()) as f:
            v_shader_txt = f.read()
        with open(getModelPath().find_file(f_shader).to_os_specific()) as f:
            f_shader_txt = f.read()
        # make the header
        if define:
            header = version + '\n'
            for name, value in define.items():
                header += '#define {0} {1}\n'.format(name, value)
            # put the header on top
            v_shader_txt = v_shader_txt.replace(version, header)
            f_shader_txt = f_shader_txt.replace(version, header)
        # make the shader
        shader = Shader.make(Shader.SL_GLSL, v_shader_txt, f_shader_txt)
        try:
            shader.set_filename(Shader.ST_vertex, v_shader)
            shader.set_filename(Shader.ST_fragment, f_shader)
        except:
            print('Shader filenames will not be available, consider using a dev version of Panda3D')
        return shader

    def get_mouse(self):
        if self.mouse_watcher_node.has_mouse():
            return self.mouse_watcher_node.get_mouse()
        else:
            return None

    def send(self, event, sentArgs=[], taskChain = None):
        """
        Wrapper for messenger.send() as messenger no longer lives in the buildins

        Send this event, optionally passing in arguments

        event is usually a string.
        sentArgs is a list of any data that you want passed along to the
            handlers listening to this event.

        If taskChain is not None, it is the name of the task chain
        which should receive the event.  If taskChain is None, the
        event is handled immediately.  Setting a non-None taskChain
        will defer the event (possibly till next frame or even later)
        and create a new, temporary task within the named taskChain,
        but this is the only way to send an event across threads.
        """
        self.messenger.send(event, sentArgs, taskChain)

    #DirectObject functions:
    #Moved here to have snake_case functions
    #and no buildins messenger and taskMgr
    def accept(self, event, method, extraArgs=[]):
        return self.messenger.accept(event, self, method, extraArgs, 1)

    def accept_once(self, event, method, extraArgs=[]):
        return self.messenger.accept(event, self, method, extraArgs, 0)

    def ignore(self, event):
        return self.messenger.ignore(event, self)

    def ignore_all(self):
        return self.messenger.ignoreAll(self)

    def is_accepting(self, event):
        return self.messenger.isAccepting(event, self)

    def get_all_accepting(self):
        return self.messenger.getAllAccepting(self)

    def is_ignoring(self, event):
        return self.messenger.isIgnoring(event, self)

    #This function must be used if you want a managed task
    def add_task(self, *args, **kwargs):
        if(not hasattr(self,"_taskList")):
            self._taskList = {}
        kwargs['owner']=self
        task = self.task_mgr.add(*args, **kwargs)
        return task

    def do_method_later(self, *args, **kwargs):
        if(not hasattr(self,"_taskList")):
            self._taskList ={}
        kwargs['owner']=self
        task = self.task_mgr.doMethodLater(*args, **kwargs)
        return task

    def remove_task(self, taskOrName):
        if type(taskOrName) == type(''):
            # we must use a copy, since task.remove will modify self._taskList
            if hasattr(self, '_taskList'):
                taskListValues = list(self._taskList.values())
                for task in taskListValues:
                    if task.name == taskOrName:
                        task.remove()
        else:
            taskOrName.remove()

    def remove_all_tasks(self):
        if hasattr(self,'_taskList'):
            for task in list(self._taskList.values()):
                task.remove()

    def _addTask(self, task):
        self._taskList[task.id] = task

    def _clearTask(self, task):
        del self._taskList[task.id]
