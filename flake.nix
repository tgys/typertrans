{
  description = "Python environment with virtualenv and requirements.txt";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python3;
        venvDir = ".venv";
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            python
            pkgs.python3Packages.pip
            
            # Essential Python packages
            pkgs.python3Packages.requests
            pkgs.python3Packages.beautifulsoup4
            pkgs.python3Packages.lxml
            pkgs.python3Packages.httpx
            pkgs.python3Packages.langdetect
            pkgs.python3Packages.deep-translator
            pkgs.python3Packages.npyscreen
            pkgs.python3Packages.pypdf2
            
            # OCR and image processing packages
            pkgs.python3Packages.numpy
            pkgs.python3Packages.opencv4
            pkgs.python3Packages.pillow
            pkgs.python3Packages.pdf2image
            pkgs.python3Packages.pytesseract
            
            #pkgs.chromium
            #pkgs.chromedriver
	    pkgs.geckodriver
            pkgs.firefox-esr
            pkgs.tesseract
            pkgs.tesseract4
            pkgs.poppler_utils  # For pdf2image
            pkgs.xclip          # For clipboard support
            pkgs.xsel           # Alternative clipboard tool
            
            # System libraries required for numpy/opencv C extensions
            pkgs.stdenv.cc.cc.lib    # Provides libstdc++.so.6 and other C++ runtime libraries
            pkgs.gcc-unwrapped       # GCC libraries
            pkgs.glibc               # Core C library
            pkgs.zlib                # Compression library (needed by various packages)
            pkgs.libffi              # Foreign function interface library
            pkgs.openssl             # SSL/TLS library
            
            # Additional libraries for OpenCV
            pkgs.libGL               # OpenGL library
            pkgs.glib                # GLib library
            pkgs.glib.dev            # GLib development files (includes libgthread)
            pkgs.xorg.libSM          # X11 Session Management library
            pkgs.xorg.libICE         # X11 Inter-Client Exchange library
            pkgs.xorg.libX11         # X11 library
            pkgs.xorg.libXext        # X11 extension library
            
            # Libraries for image processing
            pkgs.libjpeg             # JPEG library
            pkgs.libpng              # PNG library
            pkgs.libtiff             # TIFF library
            pkgs.libwebp             # WebP library
            
            # Keep only essential system tools, let pip handle Python packages
            # pkgs.python3Packages.numpy - now via pip to avoid conflicts
            # pkgs.python3Packages.opencv4 - now via pip (opencv-python)
            # pkgs.python3Packages.pillow - now via pip to avoid _imaging issues
            # pkgs.python3Packages.pdf2image - now via pip
            # pkgs.python3Packages.pytesseract - now via pip
          ];
          shellHook = ''
            # Create a function to set library paths only when needed for Python
            setup_python_libs() {
              export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.zlib}/lib:${pkgs.libffi}/lib:${pkgs.openssl}/lib:${pkgs.glibc}/lib:$LD_LIBRARY_PATH"
              export LD_LIBRARY_PATH="${pkgs.libGL}/lib:${pkgs.glib.out}/lib:${pkgs.xorg.libSM}/lib:${pkgs.xorg.libICE}/lib:${pkgs.xorg.libX11}/lib:${pkgs.xorg.libXext}/lib:$LD_LIBRARY_PATH"
              export LD_LIBRARY_PATH="${pkgs.libjpeg}/lib:${pkgs.libpng}/lib:${pkgs.libtiff}/lib:${pkgs.libwebp}/lib:$LD_LIBRARY_PATH"
            }
            
            # Create Python wrapper that sets up libraries only when running Python
            mkdir -p .nix-bin
            cat > .nix-bin/python << EOF
#!/run/current-system/sw/bin/bash
# Set up library paths for Python execution
export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.gcc-unwrapped}/lib:${pkgs.gcc-unwrapped}/lib64:${pkgs.zlib}/lib:${pkgs.libffi}/lib:${pkgs.openssl}/lib:${pkgs.glibc}/lib:\$LD_LIBRARY_PATH"
export LD_LIBRARY_PATH="${pkgs.libGL}/lib:${pkgs.glib.out}/lib:${pkgs.xorg.libSM}/lib:${pkgs.xorg.libICE}/lib:${pkgs.xorg.libX11}/lib:${pkgs.xorg.libXext}/lib:\$LD_LIBRARY_PATH"
export LD_LIBRARY_PATH="${pkgs.libjpeg}/lib:${pkgs.libpng}/lib:${pkgs.libtiff}/lib:${pkgs.libwebp}/lib:\$LD_LIBRARY_PATH"
exec ${python}/bin/python "\$@"
EOF
            chmod +x .nix-bin/python
            
            # Add our wrapper to PATH (before system python)
            export PATH="$(pwd)/.nix-bin:$PATH"
            
            # Skip virtual environment to avoid numpy conflicts with Nix packages
            # The Python wrapper will handle library paths directly
            echo "🐍 Using Nix Python with wrapper (no venv needed)"

            echo "🔧 Using system tesseract/poppler binaries with pip-installed Python packages"
            echo "📦 Installing all Python dependencies via pip for better compatibility"
            echo "🔗 System libraries added to LD_LIBRARY_PATH for numpy/opencv support"

            # Set DeepL API key
            export DEEPL_API_KEY="154cd6a6-a10f-4a4f-a830-76b48eb237af"
            echo "🌍 DeepL API key set - translation enabled"
            
            # Load additional environment variables from .env file if it exists
            if [ -f .env ]; then
              echo "📄 Loading additional environment variables from .env file..."
              export $(grep -v '^#' .env | xargs)
            fi

            echo "📦 All Python dependencies provided by Nix packages"
            echo "🧪 Checking package availability..."
            python -c "
try:
    import requests, beautifulsoup4, langdetect, numpy, cv2, PIL, pytesseract
    print('✅ All essential packages available')
except ImportError as e:
    print(f'⚠️  Some packages missing: {e}')
"
            
            echo "🧪 Testing OCR library availability..."
            echo "💡 Python libraries will auto-configure when running python commands"
            echo "🔧 LD_LIBRARY_PATH is now isolated to Python execution only"
          '';
        };
      }
    );
}
