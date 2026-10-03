"""Executa o notebook com kernel Jupyter em diretório isolado; ferramentas opcionais."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from zipfile import ZipFile
import nbformat
from nbclient import NotebookClient


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "notebooks/Figuras_Artigo_Classificador_Noticias.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    with tempfile.TemporaryDirectory(prefix="pauta-notebook-") as temporary:
        work = Path(temporary)
        # Kernel específico evita usar acidentalmente outro ambiente Python.
        kernel = work / "jupyter/kernels/pauta-artigo"
        kernel.mkdir(parents=True)
        (kernel / "kernel.json").write_text(json.dumps({"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                                                       "display_name": "Pauta Artigo", "language": "python"}), encoding="utf-8")
        environment = {**os.environ, "JUPYTER_PATH": str(work / "jupyter"), "IPYTHONDIR": str(work / "ipython"),
                       "JUPYTER_RUNTIME_DIR": str(work / "runtime"), "MPLCONFIGDIR": str(work / "matplotlib")}
        old_path = os.environ.get("JUPYTER_PATH")
        os.environ["JUPYTER_PATH"] = environment["JUPYTER_PATH"]
        shutil.copyfile(root / "reports/artigo/dados_artigo.zip", work / "dados_artigo.zip")
        try:
            client = NotebookClient(notebook, timeout=180, kernel_name="pauta-artigo", resources={"metadata": {"path": str(work)}})
            client.execute(env=environment)
        finally:
            if old_path is None:
                os.environ.pop("JUPYTER_PATH", None)
            else:
                os.environ["JUPYTER_PATH"] = old_path
        with ZipFile(work / "saida_artigo.zip") as archive:
            names = archive.namelist()
            assert len([n for n in names if n.startswith("figuras/")]) == 27
            assert len([n for n in names if n.startswith("tabelas/")]) == 24
        target = root / "reports/artigo/notebook_executado.ipynb"
        nbformat.write(notebook, target)
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        assert all(c.execution_count is not None for c in code_cells)
        print(f"Notebook aprovado: {len(code_cells)} células executadas; 27 figuras e 24 arquivos de tabelas. {target}")


if __name__ == "__main__":
    main()
