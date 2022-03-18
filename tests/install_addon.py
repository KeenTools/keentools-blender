import sys
import bpy

assert(sys.argv.index("--") != -1)
assert(sys.argv.index("--"))
script_argv = sys.argv[sys.argv.index("--") + 1:]
assert(len(script_argv) == 2)

addon_path = script_argv[0]
pkt_path = script_argv[1]
bpy.ops.preferences.addon_install(filepath=addon_path)
bpy.ops.preferences.addon_enable(module='keentools_facebuilder')
bpy.ops.wm.save_userpref()

import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt
pkt.install_core_from_file(pkt_path)
