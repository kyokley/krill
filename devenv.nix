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
      network_host = if config.env.USE_HOST_NET == 1
      then "--network=host" else "";
      net_host = if config.env.USE_HOST_NET == 1
      then "--net=host" else "";
    in {
    hello.exec = ''
      echo Welcome to $GREET
    '';
    build.exec = ''
      docker build --target=prod -t kyokley/krill-base ${network_host} .
    '';
    build-nix.exec = ''
      docker build -f Dockerfile-nix -t kyokley/krill-base-nix ${network_host} .
    '';
    run.exec = ''
      docker run --rm -it -v .:/files ${net_host} kyokley/krill-base -S /files/sources.txt -u 10 -t 2
    '';
    run-nix.exec = ''
      docker run --rm -it -v .:/files ${net_host} kyokley/krill-base-nix -S /files/sources.txt -u 10 -t 2
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
