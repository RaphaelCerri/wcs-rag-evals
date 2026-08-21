from wcs_rag_evals.chunking import chunk_markdown, chunk_openapi


def test_markdown_chunking_is_heading_aware_and_deterministic() -> None:
    text = "# Inventory\nalpha beta gamma delta epsilon\n## Projection\nzeta eta theta"
    arguments = {
        "document_id": "source/doc.md",
        "source_id": "source",
        "source_path": "doc.md",
        "authority": "source_of_truth",
        "text": text,
        "max_words": 4,
        "overlap_words": 1,
    }

    first = chunk_markdown(**arguments)
    second = chunk_markdown(**arguments)

    assert first == second
    assert [chunk.heading for chunk in first] == [
        "Inventory",
        "Inventory",
        "Inventory > Projection",
    ]
    assert first[0].text.endswith("alpha beta gamma delta")
    assert first[1].text.endswith("delta epsilon")
    assert len({chunk.chunk_id for chunk in first}) == 3


def test_openapi_chunking_creates_one_unit_per_operation() -> None:
    text = """
openapi: 3.0.3
info:
  title: Inventory API
  version: 1.0.0
paths:
  /stock:
    get:
      summary: Read stock
      operationId: getStock
    post:
      summary: Adjust stock
      operationId: adjustStock
components:
  schemas:
    Stock:
      type: object
      description: Current stock projection
"""

    chunks = chunk_openapi(
        "source/inventory.yaml",
        "source",
        "inventory.yaml",
        "source_of_truth",
        text,
    )

    assert [chunk.heading for chunk in chunks] == [
        "API information",
        "GET /stock",
        "POST /stock",
        "components > schemas > Stock",
    ]
    assert all(chunk.kind == "openapi" for chunk in chunks)
