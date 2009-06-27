# This file contains the code needed to build a Ren'Py distribution.

init python:
    import os
    import os.path
    import zipfile
    import tarfile
    import time
    import sys
    import zlib
    zlib.Z_DEFAULT_COMPRESSION = 9

    import pefile
    
    # These are files that are ignored wherever they are found in a
    # distribution.
    ignored_files = (
        "thumbs.db",
        "traceback.txt",
        "errors.txt",
        "saves"
        )

    # These are files (and directories) that are ignored when found in
    # the root directory of the distribution.
    root_ignored_files = (
        "common",
        "renpy",
        "renpy.code",
        "python23.dll",
        "python24.dll",
        "python25.dll",
        "msvcr71.dll",                     
        "lib",
        "iliad-icon.png",
        "manifest.xml",
        "icon.ico",
        "icon.icns",
        "launcherinfo.py",
        "archived",
        )

    # Extensions that should be made executable.
    executable_extensions = (
        "MacOS",
        "so",
        "dylib",
        ".sh",
        )
    

    def tree(
        src,
        dest,
        exclude_suffix=[ ".pyc", "~", ".bak" ],
        exclude_prefix=[ "#", "." ],
        exclude_files = set(ignored_files),
        root_exclude_suffix = [ ".py", ".sh", ".app" ],
        root_exclude_files = set(root_ignored_files),
        root=False):

        """
         Returns a list of source-filename, destination-filename pairs.
         """

        if dest[0] != "/":
            raise Exception("Destination must begin with /: %r" % dest)

        src = src.rstrip('/')
        dest = dest.rstrip('/')

        def include(fn, is_root):
            """
             Returns True if the file should be included in the list of
             files we are copying.
             """

            for i in exclude_suffix:
                if fn.endswith(i):
                    return False

            for i in exclude_prefix:
                if fn.startswith(i):
                    return False

            if fn in exclude_files:
                return False

            if not root or not is_root:
                return True

            for i in root_exclude_suffix:
                if fn.endswith(i):
                    return False

            if fn in root_exclude_files:
                return False

            return True
        
        rv = [ ]
        
        # Walk the tree, including what is necessary.
        for srcdir, dirs, files in os.walk(src):

            is_root = (srcdir == src)
            
            srcdir += "/"
            destdir = dest + srcdir[len(src):]
            destdir.replace("\\", "/")
            
            rv.append((srcdir, destdir))

            for fn in files:
                
                if not include(fn, is_root):
                    continue

                sfn = srcdir + fn
                dfn = destdir + fn
                    
                rv.append((sfn, dfn))

            dirs[:] = [ i for i in dirs if include(i, is_root) ]

        return rv

    def make_zip(filename, files, file_data):
        """
         This creates `filename`.zip, containing `files`, placed in the
         `filename` directory. `file_data` is a map from source file to
         replacement data.
         """

        files.sort(key=lambda a : a[1])
        
        zf = zipfile.ZipFile(filename + ".zip", "w", zipfile.ZIP_DEFLATED)
        progress_len = len(files)

        for i, (fn, an) in enumerate(files):

            if os.path.isdir(fn):
                continue

            zi = zipfile.ZipInfo(filename + an)

            
            s = os.stat(fn)
            zi.date_time = time.gmtime(s.st_mtime)[:6]
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3

            for i in executable_extensions:
                if os.path.dirname(fn).endswith(i) or fn.endswith(i):
                    zi.external_attr = long(0100777) << 16 
            else:
                zi.external_attr = long(0100666) << 16 

            if fn in file_data:
                data = file_data[fn]
            else:
                data = file(fn, "rb").read()

            zf.writestr(zi, data)

        zf.close()
        

    
    def dist_exists(fn):
        """
         Returns true if the given file exists in the renpy directory.
         """
        
        return os.path.exists(os.path.join(config.renpy_base, fn))


label distribute:

    # call lint

    # if not yesno("Building Distributions", 
    #              "I've just performed a lint on your project. If it contains errors, you should say no and fix them.\nPlease also check {a=http://www.renpy.org/wiki/renpy/Download_Ren'Py}www.renpy.org{/a} to see if updates or fixes are available.\n\nDo you want to continue?"):

    #     jump top

    python hide:

        # Do we have the files?
        has_windows = dist_exists("renpy.exe")
        has_linux = dist_exists("lib/linux-x86")
        has_mac = dist_exists("renpy.app")
        has_all = has_windows and has_mac and has_linux

        # Should we build these distributions?
        build_windows = has_windows and project.info.get("build_windows", has_windows)
        build_linux = has_linux and project.info.get("build_linux", has_linux)
        build_mac = has_mac and project.info.get("build_mac", has_mac)
        build_all = has_all and project.info.get("build_all", False)

        # The base name of the distribution.
        base_name = project.info.get("distribution_base", project.name)

        # The executable name.
        executable_name = project.info.get("executable_name", project.name)

        # Extensions to exclude.
        ignore_extensions = project.info.get("ignore_extensions", "~ .bak")

        # Documentation extensions.
        documentation_extensions = project.info.get("documentation_extensions", "txt html")
                
        # Prompt the user for all of the above.

        while True:
        
            set_tooltip("")
            screen()
            
            ui.vbox()

            title("Building Distributions")

            text_variable(_("Base Name:"), base_name, "base_name",
                          _("Used to generate the names of directories and archive files."))

            text_variable(_("Executable Name:"), executable_name, "executable_name",
                          _("Used to generate the names of executables and runnable programs."))

            text_variable(_("Ignore Extensions:"), ignore_extensions, "ignore_extensions",
                          _("Files with these extensions will not be included in the distributions."))

            text_variable(_("Documentation Extensions:"), documentation_extensions, "documentation_extensions",
                          _("Files with these extensions will be treated as documentation, when building the Macintosh application."))

            text(_("Distributions to Build:"))

            if has_windows:
                toggle_button(_("Windows x86"), build_windows, ui.returns("build_windows"),
                              _("Zip distribution for the 32-bit Windows platform."))

            if has_linux:
                toggle_button(_("Linux x86"), build_linux, ui.returns("build_linux"),
                              _("Tar.Bz2 distribution for the Linux x86 platform."))

            if has_mac:
                toggle_button(_("Macintosh Universal Application"), build_mac, ui.returns("build_mac"),
                              _("Single application distribution for the Macintosh x86 and ppc platforms."))

            if has_all:
                toggle_button(_("Windows/Linux/Mac Combined"), build_all, ui.returns("build_all"),
                              _("Zip distribution for the Windows x86, Linux x86, Macintosh x86 and Macintosh ppc platforms."))
                

            ui.null(height=15)
            
            button(_("Build"), ui.returns("build"), _("Start building the distributions."))
            button(_("Cancel"), ui.jumps("top", ""), "")

            ui.close()

            act = interact()

            if act == "build_windows":
                build_windows = not build_windows
            elif act == "build_linux":
                build_linux = not build_linux
            elif act == "build_mac":
                build_mac = not build_mac
            elif act == "build_all":
                build_all = not build_all
            elif act == "base_name":

                base_name = input(
                    _("Base Name"),
                    _("Please enter in the base name for your distribution. This name is used to generate the names of directories and archive files. Usually, this is the name of your game, plus a version number, like \"moonlight-1.0\"."),
                    base_name)

            elif act == "executable_name":
                
                executable_name = input(
                    _("Executable Name"),
                    _("Please enter a name for the executables in your distribution. This should not include an extension, as that will be added automatically."),
                    executable_name)
            
            elif act == "ignore_extensions":

                ignore_extensions = input(
                    _("Ignore Extensions"),
                    _("Please enter a space-separated list of file extensions. Files with these extensions will not be included in the built distributions."),
                    ignore_extensions)

            elif act == "documentation_extensions":

                documentation_extensions = input(
                    _("Documentation Extensions"),
                    _("Please enter a space separated list of documentation extensions. Files in the base directory with these extensions will have a second copy stored outside of the Macintosh application."),
                    documentation_extensions)
                
            elif act == "build":
                break

        # Store the user-selected options in info, and save info.

        project.info["distribution_base"] = base_name
        project.info["executable_name"] = executable_name
        project.info["ignore_extensions"] = ignore_extensions
        project.info["documentation_extensions"] = documentation_extensions

        project.info["build_windows"] = build_windows
        project.info["build_linux"] = build_linux
        project.info["build_mac"] = build_mac
        project.info["build_all"] = build_all

        project.save()

        # Convert some of these to more useful formats.
        ignore_extensions = [ i.strip() for i in ignore_extensions.split() ]
        documentation_extensions = [ i.strip() for i in documentation_extensions.split() ]
        
        # Scan for the files we want to include in the various distributions.
        
        info(
            _("Building Distributions"),
            _("Scanning directories to determine which files to include."),
            )

        # Files included in the various distributions.
        multi_files = [ ]
        win_files = [ ]
        linux_files = [ ]
        mac_files = [ ]

        # A map from source file name to replacement data to be placed in
        # that file.
        file_data = { }
        
        
        ######################################################################
        # Multi files.

        rb = config.renpy_base + "/"
        
        # Project files.
        multi_files.extend(tree(project.path, "/", root=True, exclude_suffix=ignore_extensions))
        multi_files.append((rb + "renpy.py",  "/" + executable_name + ".py"))
        
        # Renpy files.
        multi_files.extend(tree(rb + "common", "/common"))
        multi_files.extend(tree(rb + "renpy", "/renpy"))
        multi_files.append((rb + "LICENSE.txt", "/renpy/LICENSE.txt"))
        
        def add_script_version(fn, ignore_extensions=ignore_extensions, multi_files=multi_files, rb=rb):
            """
             Add a script_version file if it does not already exist, and if the
             extension is allowed by the game.
             """

            for a, b in multi_files:
                if b == "/game/" + fn:
                    return

            for i in ignore_extensions:
                if fn.endswith(i):
                    return

            multi_files.append((rb + "launcher/" + fn, "/game/" + fn))

        add_script_version("script_version.rpy")
        add_script_version("script_version.rpyc")

        
        ######################################################################
        # Windows files.

        if build_windows or build_all:

            win_files.append((rb + "renpy.exe", "/" + executable_name + ".exe"))
            win_files.append((rb + "renpy.code", "/renpy.code"))
            win_files.append((rb + "python25.dll", "/python25.dll"))
            win_files.append((rb + "msvcr71.dll", "/msvcr71.dll"))

            if os.path.exists(project.path + "/icon.ico"):
                file_data[rb + "renpy.exe"] = pefile.change_icons(
                    rb + "renpy.exe",
                    project.path + "/icon.ico",
                    )

                
        ######################################################################
        # Linux files.
        
        if build_linux or build_all:

            linux_files.append((rb + "renpy.sh", "/" + executable_name + ".sh"))
            linux_files.append((rb + "lib", "/lib"))
            linux_files.append((rb + "lib/python", "/lib/python"))
            linux_files.append(tree(rb + "lib/linux-x86", "/lib/linux-x86"))

            # Warning: The tar.bz2 builder doesn't support file_data.

            
        ######################################################################
        # Mac (non-app) files.
        
        if build_mac or build_all:
            mac_files = tree(rb + "renpy.app",
                             "/" + executable_name + ".app")

            # Rename executable.
            mac_files = [ (fn, an.replace("Ren'Py Launcher", executable_name)) for (fn, an) in mac_files ]

            # Plist file.
            quoted_name = executable_name.replace("&", "&amp;").replace("<", "&lt;")                                               
            info_plist = file(rb + "renpy.app/Contents/Info.plist", "rb").read().replace("Ren'Py Launcher", quoted_name)
            file_data[rb + "renpy.app/Contents/Info.plist"] = info_plist

            # Launcher script.
            quoted_name = executable_name.replace("\"", "\\\"")
            launcher_py = file(rb + "renpy.app/Contents/Resources/launcher.py", "rb").read().replace("Ren'Py Launcher", quoted_name)
            file_data[rb + "renpy.app/Contents/Resources/launcher.py"] = launcher_py

            # Icon file.
            if os.path.exists(project.path + "/icon.icns"):
                icon_data = file(project.path + "/icon.icns", "rb").read()
                file_data[rb + "renpy.app/Contents/Resources/launcher.icns"] = icon_data


        ######################################################################
        # Now, build the various distributions.

        if build_windows:
            make_zip(
                base_name + "-win32",
                multi_files + win_files,
                file_data)
                    
    jump top
        