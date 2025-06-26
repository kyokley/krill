{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/basics/
  env = {
    GREET = "Krill";
    USE_HOST_NET = 1;
    PYTHONPATH=".";
  };

  # https://devenv.sh/packages/
  packages = [
    pkgs.gnumake
    pkgs.docker
  ];

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    version = "3.12";
    uv = {
      enable = true;
      sync.enable = true;
    };
  };

  # https://devenv.sh/processes/
  # processes.cargo-watch.exec = "cargo-watch";

  # https://devenv.sh/services/
  # services.postgres.enable = true;

  # https://devenv.sh/scripts/
  scripts = let
      host_net = if config.env.USE_HOST_NET == 1
      then "--network=host" else "";
    in {
    hello.exec = ''
      echo Welcome to $GREET
    '';
    build.exec = ''
      docker build --target=prod -t kyokley/krill-base ${host_net} .
    '';
    build-nix.exec = ''
      docker build -f Dockerfile-nix -t kyokley/krill-base-nix ${host_net} .
    '';
  };

  enterShell = ''
    hello
  '';

  # https://devenv.sh/tasks/
  # tasks = {
  #   "myproj:setup".exec = "mytool build";
  #   "devenv:enterShell".after = [ "myproj:setup" ];
  # };

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    uv run pytest
  '';

  # https://devenv.sh/git-hooks/
  git-hooks.hooks = {
    ruff.enable = true;
    ruff-format.enable = true;
    isort = {
      enable = true;
      settings.profile = "black";
    };
  };

  # See full reference at https://devenv.sh/reference/options/
}
