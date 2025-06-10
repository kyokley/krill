{
  pkgs ? import <nixpkgs> {},
  # pkgsLinux ? import <nixpkgs> {system = "x86_64-linux";}
  }:

  pkgs.dockerTools.buildImage {
    name = "krill-base";
    tag = "latest";

    copyToRoot = pkgs.buildEnv {
      name = "image-root";
      paths = [
        pkgs.python313Packages.uv
        pkgs.busybox
        ./.
      ];
      pathsToLink = [ "/bin" ];
    };

    runAsRoot = ''
      cd /bin
    '';

    config = {
      Cmd = [ "/bin/ls" ];
    };
  }
