class NabdcodeCli < Formula
  include Language::Python::Virtualenv

  desc "Local AI coding agent with MCP, skills system and personalized memory"
  homepage "https://github.com/nabdcode/nabdcode-cli"
  url "https://github.com/nabdcode/nabdcode-cli/archive/refs/tags/v0.1.0-beta.tar.gz"
  sha256 "0019dfc4b32d63c1392aa264aed2253c1e0c2fb09216f8e2cc269bbfb8bb49b5"
  license "MIT"

  depends_on "python@3.12"
  depends_on "node"

  def install
    venv = virtualenv_create(libexec, "python3.12")
    venv.pip_install_and_link buildpath
    bin.install_symlink(libexec/"bin/nabdcode-cli")
  end

  def post_install
    (etc/"nabdcode").mkpath
    (var/"nabdcode").mkpath
    (var/"nabdcode/cache").mkpath
    (var/"nabdcode/skills").mkpath
  end

  test do
    output = shell_output("#{bin}/nabdcode-cli --version")
    assert_match "0.1.0", output
  end
end
