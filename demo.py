from __future__ import print_function
from PandaApp import PandaApp
from direct.interval.IntervalGlobal import *

class Demo(PandaApp):

    def __init__(self):
        #init the base class py3 style
        #super().__init__()
        #py2 style
        super(Demo, self).__init__()

        #load a model, and reparent it to render
        #model=self.loader.load_model('frowney')
        #model.reparent_to(self.render)
        #or a shorter way...
        model=self.load_model('frowney', parent=self.render)
        #put it somewhere visible
        model.set_pos(0, 10, 0)

        #interval test
        LerpHprInterval(model, 5.0, (360, 0, 360), startHpr=(0, 0, 0)).loop()

        #task and mouse test
        self.i_has_mouse=True
        self.add_task(self.mouse_test, 'mouse_test_tsk')

        #test mouse input
        self.accept('mouse1', print, ['click!'])
        #test key input
        self.accept('escape', self.exit)

        #test window resize event
        self.accept('window-event-resize', print, ['Size of the window changed'])

        #test exit event
        #this one fires when the window is closed by the user
        self.accept('window-event-close', print, ['Window got closed!'])
        #this one fires before sys.exit
        self.accept('exit', print, ['Shutting down!'])

        #run the PandaApp
        self.run()

    def mouse_test(self, task):
        if self.focus:
            if self.get_mouse():
                if not self.i_has_mouse:
                    print ("Hello mr.Mouse")
                self.i_has_mouse=True
            else:
                if self.i_has_mouse:
                    print("Bye-bye mr.Mouse")
                    self.i_has_mouse=False
        return task.cont

my_app=Demo()

