import sys
import os 
import subprocess
import shutil
import tempfile
import contextlib
import distutils


# --------------- from cupy/install/build.py ----------------
PLATFORM_DARWIN = sys.platform.startswith('darwin')
PLATFORM_LINUX = sys.platform.startswith('linux')
PLATFORM_WIN32 = sys.platform.startswith('win32')

minimum_cuda_version = 8000

_cuda_path = 'NOT_INITIALIZED'
_compiler_base_options = None

_cuda_version = None


@contextlib.contextmanager
def _tempdir():
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
# -----------------------------------------------------------


# --------------- from cupy/install/utils.py ----------------
def print_warning(*lines):
    print('**************************************************')
    for line in lines:
        print('*** WARNING: %s' % line)
    print('**************************************************')

def get_path(key):
    return os.environ.get(key, '').split(os.pathsep)

def search_on_path(filenames):
    for p in get_path('PATH'):
        for filename in filenames:
            full = os.path.join(p, filename)
            if os.path.exists(full):
                return os.path.abspath(full)
    return None
# -----------------------------------------------------------


def _run_nvcc(cmd, cwd):
    try:
        return subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        msg = ('`nvcc` command returns non-zero exit status. \n'
               'command: {0}\n'
               'return-code: {1}\n'
               'stdout/stderr: \n'
               '{2}'.format(e.cmd,
                            e.returncode,
                            e.output.decode(encoding='UTF-8',
                                            errors='replace')))
        raise RuntimeError(msg)
    except OSError as e:
        msg = 'Failed to run `nvcc` command. ' \
              'Check PATH environment variable: ' \
              + str(e)
        raise OSError(msg)


def build_and_run(nvcc_path, source):
    with _tempdir() as temp_dir:
        fname = os.path.join(temp_dir, 'a.cu')
        with open(fname, 'w') as f:
            f.write(source)

        # TODO: rewrite _run_nvcc so that we use it twice here
        # build
        build_out = _run_nvcc([nvcc_path, 'a.cu', '-o', 'test.out'], temp_dir)

        # and run
        run_out = subprocess.check_output(['./test.out'], cwd=temp_dir, stderr=subprocess.STDOUT)
        return run_out


# adapted from cupy/install/build.py
# TODO: remove the settings arg?
def check_cuda_version(nvcc_path, settings):
    global _cuda_version

    source = '''
             #include <cuda.h>
             #include <stdio.h>
             int main(int argc, char* argv[]) {
               printf("%d", CUDA_VERSION);
               return 0;
             }
             '''

    try:
        out = build_and_run(nvcc_path, source)
        #                    include_dirs=settings['include_dirs'])
    except Exception as e:
        print_warning('Cannot check CUDA version', str(e))
        return False

    _cuda_version = int(out)

    if _cuda_version < minimum_cuda_version:
        print_warning(
            'CUDA version is too old: %d' % _cuda_version,
            'CUDA v7.0 or newer is required')
        return False

    return True


# adapted from cupy/install/build.py
def get_cuda_version(nvcc_path, settings):
    """Return CUDA Toolkit version cached in check_cuda_version()."""

    global _cuda_version
    if _cuda_version is None:
        check_cuda_version(nvcc_path, settings)
    return _cuda_version


# adapted from cupy.cupy_setup_build._nvcc_gencode_options()
def nvcc_arch_options(cuda_version):
    """Returns NVCC GPU architechture options."""

    arch_list = ['sm_30', 'sm_35', 'sm_50']

    if cuda_version >= 8000:
        arch_list += ['sm_60', 'sm_61']

    if cuda_version >= 9000:
        arch_list += ['sm_70']
                      
    #options = []
    #for arch in arch_list:
    #    options.append((arch, '-arch={}'.format(arch)))

    #return options
    return arch_list


def get_cuda_path():
    global _cuda_path

    # Use a magic word to represent the cache not filled because None is a
    # valid return value.
    if _cuda_path is not 'NOT_INITIALIZED':
        return _cuda_path

    nvcc_path = search_on_path(('nvcc', 'nvcc.exe'))
    cuda_path_default = None
    if nvcc_path is None:
        print_warning('nvcc not in path.',
                      'Please set path to nvcc.')
    else:
        cuda_path_default = os.path.normpath(
            os.path.join(os.path.dirname(nvcc_path), '..'))

    cuda_path = os.environ.get('CUDA_PATH', '')  # Nvidia default on Windows
    if len(cuda_path) > 0 and cuda_path != cuda_path_default:
        print_warning(
            'nvcc path != CUDA_PATH',
            'nvcc path: %s' % cuda_path_default,
            'CUDA_PATH: %s' % cuda_path)

    if os.path.exists(cuda_path):
        _cuda_path = cuda_path
    elif cuda_path_default is not None:
        _cuda_path = cuda_path_default
    elif os.path.exists('/usr/local/cuda'):
        _cuda_path = '/usr/local/cuda'
    else:
        _cuda_path = None

    return _cuda_path


def get_nvcc_path():
    nvcc = os.environ.get('NVCC', None)
    if nvcc:
        return distutils.util.split_quoted(nvcc)

    cuda_path = get_cuda_path()
    if cuda_path is None:
        return None

    if PLATFORM_WIN32:
        nvcc_bin = 'bin/nvcc.exe'
    else:
        nvcc_bin = 'bin/nvcc'

    nvcc_path = os.path.join(cuda_path, nvcc_bin)
    if os.path.exists(nvcc_path):
        return [nvcc_path]
    else:
        return None


def get_compiler_setting():
    cuda_path = get_cuda_path()

    include_dirs = []
    library_dirs = []
    define_macros = []

    if cuda_path:
        include_dirs.append(os.path.join(cuda_path, 'include'))
        if PLATFORM_WIN32:
            library_dirs.append(os.path.join(cuda_path, 'bin'))
            library_dirs.append(os.path.join(cuda_path, 'lib', 'x64'))
        else:
            library_dirs.append(os.path.join(cuda_path, 'lib64'))
            library_dirs.append(os.path.join(cuda_path, 'lib'))

    if PLATFORM_DARWIN:
        library_dirs.append('/usr/local/cuda/lib')

    if PLATFORM_WIN32:
        nvtoolsext_path = os.environ.get('NVTOOLSEXT_PATH', '')
        if os.path.exists(nvtoolsext_path):
            include_dirs.append(os.path.join(nvtoolsext_path, 'include'))
            library_dirs.append(os.path.join(nvtoolsext_path, 'lib', 'x64'))
        else:
            define_macros.append(('CUPY_NO_NVTX', '1'))

    return {
        'include_dirs': include_dirs,
        'library_dirs': library_dirs,
        'define_macros': define_macros,
        'language': 'c++',
    }


def build():
    cubin_path = []

    # check nvcc exists
    nvcc_path = get_nvcc_path()
    if nvcc_path is None:
        print("nvcc is not found. Please check your"
              "PATH environmental variable", file=sys.stderr)
        return cubin_path

    if len(nvcc_path) > 1:
        print("Found multiple nvcc, use the first found one:", nvcc_path[0])
    nvcc = nvcc_path[0]   

    # get nvcc version
    settings = get_compiler_setting()
    ver = get_cuda_version(nvcc, settings)

    # get arch
    options = nvcc_arch_options(ver)

    # hard-coded source; TODO: be aware of this!
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.path.join(dir_path, 'nsls2ptycho/core/ptycho/')
    source_path = os.path.join(dir_path, 'ptycho_precision.cu')

    # actual compilation:
    for precision in ['single', 'double']:
        for arch in options:
            filename = 'ptycho_' + arch + '_' + precision + '.cubin'
            filepath = os.path.join(dir_path, filename)
            try:
                subprocess.run([nvcc, '-cubin', '-arch='+arch, '-o', filepath, source_path])
            except Exception as e:
                print(e)
            cubin_path.append(filepath)
            print('processed:', filepath)

    return cubin_path
