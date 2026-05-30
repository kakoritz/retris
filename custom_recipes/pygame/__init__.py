from os.path import join

from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory


class Pygame2Recipe(CompiledComponentsPythonRecipe):
    """
    Pygame 2.6.1 — supports Python 3.13/3.14 (longintrepr.h removed in 2.5.0).
    Overrides the p4a built-in recipe which is stuck at 2.1.0.
    """

    version = '2.6.1'
    url = 'https://github.com/pygame/pygame/archive/{version}.tar.gz'

    site_packages_name = 'pygame'
    name = 'pygame'

    depends = ['sdl2', 'sdl2_image', 'sdl2_mixer', 'sdl2_ttf', 'setuptools', 'jpeg', 'png']
    call_hostpython_via_targetpython = False
    install_in_hostpython = False
    hostpython_prerequisites = ['setuptools', 'cython>=3.0']

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            setup_template = open(join("buildconfig", "Setup.Android.SDL2.in")).read()
            env = self.get_recipe_env(arch)
            env['ANDROID_ROOT'] = join(self.ctx.ndk.sysroot, 'usr')

            png = self.get_recipe('png', self.ctx)
            png_lib_dir = join(png.get_build_dir(arch.arch), '.libs')
            png_inc_dir = png.get_build_dir(arch)

            jpeg = self.get_recipe('jpeg', self.ctx)
            jpeg_inc_dir = jpeg_lib_dir = jpeg.get_build_dir(arch.arch)

            sdl_mixer_includes = ""
            sdl2_mixer_recipe = self.get_recipe('sdl2_mixer', self.ctx)
            for include_dir in sdl2_mixer_recipe.get_include_dirs(arch):
                sdl_mixer_includes += f"-I{include_dir} "

            sdl2_image_includes = ""
            sdl2_image_recipe = self.get_recipe('sdl2_image', self.ctx)
            for include_dir in sdl2_image_recipe.get_include_dirs(arch):
                sdl2_image_includes += f"-I{include_dir} "

            setup_file = setup_template.format(
                sdl_includes=(
                    " -I" + join(self.ctx.bootstrap.build_dir, 'jni', 'SDL', 'include') +
                    " -L" + join(self.ctx.bootstrap.build_dir, "libs", str(arch)) +
                    " -L" + png_lib_dir + " -L" + jpeg_lib_dir + " -L" + arch.ndk_lib_dir_versioned),
                sdl_ttf_includes="-I"+join(self.ctx.bootstrap.build_dir, 'jni', 'SDL2_ttf'),
                sdl_image_includes=sdl2_image_includes,
                sdl_mixer_includes=sdl_mixer_includes,
                jpeg_includes="-I"+jpeg_inc_dir,
                png_includes="-I"+png_inc_dir,
                freetype_includes=""
            )
            open("Setup", "w").write(setup_file)

            # The Android Setup template omits the SIMD blitter sources from the
            # surface module.  alphablit.c references symbols from both files at
            # link time regardless of architecture:
            #   simd_blitters_sse2.c — defines alphablit_alpha_sse2_argb_surf_alpha
            #     etc.; on ARM64 it includes sse2neon.h to translate SSE2 → NEON.
            #   simd_blitters_avx2.c — defines blit_blend_rgb_*_avx2 etc. as stubs
            #     that return 0/error on non-AVX2 hardware; pg_has_avx2() returns 0
            #     so the stubs are never called, but they must be linked.
            # Without both files surface.so has unresolved symbols and dlopen fails.
            if 'arm64' in arch.arch or 'aarch64' in arch.arch:
                content = open("Setup").read()
                content = content.replace(
                    "surface src_c/surface.c src_c/alphablit.c src_c/surface_fill.c",
                    "surface src_c/surface.c src_c/alphablit.c"
                    " src_c/simd_blitters_sse2.c src_c/simd_blitters_avx2.c"
                    " src_c/surface_fill.c",
                )
                open("Setup", "w").write(content)

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['USE_SDL2'] = '1'
        env["PYGAME_CROSS_COMPILE"] = "TRUE"
        env["PYGAME_ANDROID"] = "TRUE"
        return env


recipe = Pygame2Recipe()
