import subprocess
import sys

from pythonforandroid.recipe import PythonRecipe
from pythonforandroid.logger import info

_ARCH_PLATFORM = {
    'arm64-v8a':   'manylinux2014_aarch64',
    'armeabi-v7a': 'manylinux2014_armv7l',
    'x86':         'manylinux2014_i686',
    'x86_64':      'manylinux2014_x86_64',
}


class PygameCERecipe(PythonRecipe):
    """
    Custom recipe for pygame-ce on Android.

    p4a's built-in pip fallback runs on the x86_64 build host without
    --platform, so it downloads x86_64 wheels.  This recipe explicitly
    requests the correct manylinux2014_aarch64 (or other arch) wheel so
    the binary that ends up in the APK matches the device's ABI.
    """
    name = 'pygame_ce'
    version = '2.5.7'
    site_packages_name = 'pygame'
    call_hostpython_via_targetpython = False
    install_in_hostpython = False
    depends = ['python3', 'hostpython3']

    def install_python_package(self, arch, name=None, env=None, is_dir=True):
        platform = _ARCH_PLATFORM.get(arch.arch, 'manylinux2014_aarch64')

        ver = self.ctx.python_recipe.version.split('.')
        py_tag = ver[0] + ver[1]  # "3.14.2" → "314"

        try:
            site_packages = self.ctx.get_site_packages_dir(arch)
        except TypeError:
            site_packages = self.ctx.get_site_packages_dir()

        info(f'pygame_ce: downloading {platform} wheel for cp{py_tag}')
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            '--target', site_packages,
            '--platform', platform,
            '--python-version', py_tag,
            '--abi', f'cp{py_tag}',
            '--only-binary', ':all:',
            '--no-deps',
            '--upgrade',
            f'pygame_ce=={self.version}',
        ])


recipe = PygameCERecipe()
