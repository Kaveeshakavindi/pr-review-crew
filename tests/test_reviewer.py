import asyncio
import httpx

from app.review.reviewer import review_pull_request


async def main():

    diff = """
diff --git a/test.py b/test.py
new file mode 100644
--- /dev/null
+++ b/test.py
@@ -0,0 +1,3 @@
+password = "secret123"
+print(password)
+print("hello")
"""

    async with httpx.AsyncClient() as client:
        result = await review_pull_request(
            client,
            diff,
        )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())