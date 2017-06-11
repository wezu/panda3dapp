This is a replacement for ShowBase for starting a Panda3D application.

It opens a window, starts the task, interval, messenge, and event managers,
garbage collector task, and creates a camera and scengraph for 3D and 2D.

It uses DirectObject like interface, only in snake_case (eg. `ignore_all()` not `ignoreAll()`)

It also uses a wrapper around the Panda3D `ConfigVariable*`, use:
`self.config['win-size']`
where you would normaly use:
`ConfigVariableInt('win-size').get_value()`
or in this case:
`[ConfigVariableInt('win-size').get_word(0), ConfigVariableInt('win-size').get_word(1)]`

It will NOT:
- put things into buildins
- use NodePath-extensions
- setup sound system
- setup collision traversers
- setup camera controll
- setup wx or tk
- setup particle system
- setup physics
- setup BulletinBoard
- setup Jobs
- create render2dp, aspect2dp and any aspect2d children (a2dTop, a2dBottomCenterNs, etc)
- enforce a singelton pattern (shoot your own foot if you like)
- work on py 2.x (?)
- walk the dog, put out the trash
