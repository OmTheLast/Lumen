class LumenLocal < Formula
  include Language::Python::Virtualenv

  desc "Local-first macOS desktop agent powered by local models"
  homepage "https://lumen.ompatnaik.com"
  url "https://github.com/OmTheLast/Lumen/archive/refs/tags/v0.4.0.tar.gz"
  sha256 "7d44760c6aafd022fdf2280ab5c2f5733801e14404e859a8e3c96620719db364"
  license "MIT"
  head "https://github.com/OmTheLast/Lumen.git", branch: "main"

  depends_on :macos
  depends_on "python@3.14"

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/c9/c7/424b75da314c1045981bd9777432fad05a9e0c69daa4ed7e308bbaffe405/certifi-2026.6.17.tar.gz"
    sha256 "024c88eeec92ca068db80f02b8b07c9cef7b9fe261d1d535abfd5abd6f6af432"
  end

  resource "charset-normalizer" do
    url "https://files.pythonhosted.org/packages/e7/a1/67fe25fac3c7642725500a3f6cfe5821ad557c3abb11c9d20d12c7008d3e/charset_normalizer-3.4.7.tar.gz"
    sha256 "ae89db9e5f98a11a4bf50407d4363e7b09b31e55bc117b4f7d80aab97ba009e5"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/cd/63/9496c57188a2ee585e0f1db071d75089a11e98aa86eb99d9d7618fc1edce/idna-3.18.tar.gz"
    sha256 "ffb385a7e039654cef1ab9ef32c6fafe283c0c0467bba1d9029738ce4a14a848"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/ac/c3/e2a2b89f2d3e2179abd6d00ebd70bff6273f37fb3e0cc209f48b39d00cbf/requests-2.34.2.tar.gz"
    sha256 "f288924cae4e29463698d6d60bc6a4da69c89185ad1e0bcc4104f584e960b9ed"
  end

  resource "urllib3" do
    url "https://files.pythonhosted.org/packages/53/0c/06f8b233b8fd13b9e5ee11424ef85419ba0d8ba0b3138bf360be2ff56953/urllib3-2.7.0.tar.gz"
    sha256 "231e0ec3b63ceb14667c67be60f2f2c40a518cb38b03af60abc813da26505f4c"
  end

  def install
    virtualenv_install_with_resources(using: "python@3.14")

    system "scripts/build_macos_app.sh",
           "--runtime-root", libexec,
           "--python-path", libexec/"bin/python"
    prefix.install "dist/macos/Lumen.app"

    (bin/"lumen-app").write <<~SH
      #!/bin/bash
      open "#{opt_prefix}/Lumen.app"
    SH
  end

  def caveats
    <<~EOS
      Start the native Lumen window with:
        lumen-app

      Lumen requires a separately installed local model provider and model.
      For example:
        brew install ollama
        ollama serve
        ollama pull qwen3:latest

      Model weights are not included in this formula.
    EOS
  end

  test do
    system libexec/"bin/python", "-c", "import lumen"
    assert_path_exists prefix/"Lumen.app/Contents/MacOS/Lumen"
  end
end
