from dataclasses import dataclass
from unittest import IsolatedAsyncioTestCase
from unittest.mock import (
    AsyncMock,
    MagicMock,
    create_autospec,
    sentinel,
)

from addon_imps.storage.figshare import (
    Article,
    FigshareStorageImp,
    File,
    Project,
)
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    StorageConfig,
)


@dataclass
class _ListChildItemsArgs:
    item_id: str
    extracted_id: str
    item_type: ItemType
    method_name_to_be_called: str | None
    expected_result: ItemSampleResult


class TestFigshareStorageImp(IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = StorageConfig(
            external_api_url="https://some-api.com", max_upload_mb=123
        )
        self.network = AsyncMock(spec_set=HttpRequestor)
        self.imp = FigshareStorageImp(config=self.config, network=self.network)

    def _patch_get(self, return_value: dict | list | str):
        mock = self.network.GET.return_value.__aenter__.return_value
        mock.json_content = AsyncMock(return_value=return_value)
        mock.http_status = 200

    def _assert_get(self, url: str, query: dict = None):
        extra_params = {"query": query} if query else {}
        self.network.GET.assert_called_once_with(url, **extra_params)
        self.network.GET.return_value.__aenter__.assert_awaited_once_with()
        self.network.GET.return_value.__aenter__.return_value.json_content.assert_awaited_once_with()
        self.network.GET.return_value.__aexit__.assert_awaited_once_with(
            None, None, None
        )

    async def test_get_external_account_id(self):
        mock_response = {"id": "12345"}
        self._patch_get(mock_response)

        result = await self.imp.get_external_account_id({})

        self.assertEqual(result, "")
        self.network.GET.assert_not_called()

    async def test_list_root_items(self):
        cursor = 1
        mock_response = [MagicMock(item_result=sentinel.item_result1)]
        mock_response2 = [MagicMock(item_result=sentinel.item_result2)]

        self.imp._fetch_projects = AsyncMock(
            spec_set=self.imp._fetch_projects, return_value=mock_response
        )
        self.imp._fetch_articles = AsyncMock(
            spec_set=self.imp._fetch_articles, return_value=mock_response2
        )

        result = await self.imp.list_root_items(f"{cursor}")

        expected_result = ItemSampleResult(
            items=[sentinel.item_result1, sentinel.item_result2], next_sample_cursor="2"
        )

        self.assertEqual(expected_result, result)
        self.imp._fetch_articles.assert_awaited_once_with(1)
        self.imp._fetch_projects.assert_awaited_once_with(1)

    async def test_item_info_empty(self):
        self.imp._fetch_article = MagicMock(spec_set=self.imp._fetch_article)
        self.imp._fetch_project = MagicMock(spec_set=self.imp._fetch_project)

        self.assertEqual(
            await self.imp.get_item_info(""), ItemResult("", "", ItemType.FOLDER)
        )

        self.imp._fetch_project.assert_not_called()
        self.imp._fetch_article.assert_not_called()

    async def test_item_info_article(self):
        self.imp._fetch_article = MagicMock(
            spec_set=self.imp._fetch_article,
            return_value=MagicMock(item_result=sentinel.item_result),
        )
        self.imp._fetch_project = MagicMock(spec_set=self.imp._fetch_project)

        self.assertEqual(
            await self.imp.get_item_info("articles/123"), sentinel.item_result
        )

        self.imp._fetch_article.assert_called_once_with("123")
        self.imp._fetch_project.assert_not_called()

    async def test_item_info_project(self):
        self.imp._fetch_article = MagicMock(spec_set=self.imp._fetch_article)
        self.imp._fetch_project = MagicMock(
            spec_set=self.imp._fetch_project,
            return_value=MagicMock(item_result=sentinel.item_result),
        )
        self.assertEqual(
            await self.imp.get_item_info("projects/123"), sentinel.item_result
        )

        self.imp._fetch_project.assert_called_once_with("123")
        self.imp._fetch_article.assert_not_called()

    async def test_item_info_both(self):
        self.imp._fetch_article = MagicMock(spec_set=self.imp._fetch_article)
        self.imp._fetch_project = MagicMock(
            spec_set=self.imp._fetch_project,
            return_value=MagicMock(item_result=sentinel.item_result),
        )
        with self.assertRaises(ValueError):
            await self.imp.get_item_info("123")

        self.imp._fetch_project.assert_not_called()
        self.imp._fetch_article.assert_not_called()

    async def test_list_child_items(self):
        expected_positive_result = ItemSampleResult(
            items=[sentinel.item_result], next_sample_cursor="2"
        )
        expected_negative_result = ItemSampleResult(items=[], next_sample_cursor="2")

        cases = [
            _ListChildItemsArgs(
                "projects/123",
                "123",
                ItemType.FOLDER,
                "_fetch_project_articles",
                expected_positive_result,
            ),
            _ListChildItemsArgs(
                "projects/123",
                "123",
                None,
                "_fetch_project_articles",
                expected_positive_result,
            ),
            _ListChildItemsArgs(
                "articles/123",
                "123",
                ItemType.FOLDER,
                "_fetch_article_files",
                expected_negative_result,
            ),
            _ListChildItemsArgs(
                "projects/123",
                "123",
                ItemType.FILE,
                "_fetch_project_articles",
                expected_negative_result,
            ),
            *[
                _ListChildItemsArgs(
                    "123",
                    "123",
                    item_type,
                    None,
                    expected_negative_result,
                )
                for item_type in [None, *ItemType]
            ],
            *[
                _ListChildItemsArgs(
                    "articles/345",
                    "345",
                    item_type,
                    "_fetch_article_files",
                    expected_positive_result,
                )
                for item_type in [None, ItemType.FILE]
            ],
        ]
        mock1 = self.imp._fetch_project_articles = create_autospec(
            self.imp._fetch_project_articles,
            return_value=[MagicMock(item_result=sentinel.item_result)],
        )
        mock2 = self.imp._fetch_article_files = create_autospec(
            self.imp._fetch_article_files,
            return_value=[MagicMock(item_result=sentinel.item_result)],
        )
        mocks = [mock1, mock2]
        for case in cases:
            for mock in mocks:
                mock.reset_mock()
            with self.subTest(case=f"case: {case=}"):
                await self._test_list_collection_items_ordinary(case)

    async def _test_list_collection_items_ordinary(
        self, args: _ListChildItemsArgs
    ) -> None:
        method_names = [
            "_fetch_project_articles",
            "_fetch_article_files",
        ]
        result = await self.imp.list_child_items(
            args.item_id,
            item_type=args.item_type,
        )
        self.assertEqual(result, args.expected_result)
        for method_name in method_names:
            method = getattr(self.imp, method_name)
            if (
                method_name == args.method_name_to_be_called
                and args.expected_result.items
            ):
                method.assert_called_once_with(args.extracted_id, 1)
            else:
                method.assert_not_called()
        assert result == args.expected_result

    async def test_fetch_project_articles(self):
        cases = [
            [
                self.imp._fetch_project_articles,
                "lalala",
                "account/projects/lalala/articles",
                [{"id": 123, "title": "sdaas"}],
                [Article(id=123, title="sdaas")],
            ],
            [
                self.imp._fetch_article_files,
                456,
                "account/articles/456/files",
                [{"id": 123, "name": "sdaas"}],
                [File(id=123, name="sdaas", article_id=456)],
            ],
            [
                self.imp._fetch_articles,
                None,
                "account/articles",
                [{"id": 123, "title": "sdaas"}],
                [Article(id=123, title="sdaas")],
            ],
            [
                self.imp._fetch_projects,
                None,
                "account/projects",
                [{"id": 123, "title": "sdaas"}],
                [Project(id=123, title="sdaas")],
            ],
        ]
        for method, item_id, expected_path, response_json, expected_result in cases:
            with self.subTest(f"case={method.__name__}"):
                self.network.reset_mock()
                self._patch_get(response_json)
                if item_id:
                    result = await method(item_id, 1)
                else:
                    result = await method(1)
                self.assertEqual(expected_result, result)

                self._assert_get(expected_path, query={"page": 1, "page_size": 20})

    async def test_fetch_project(self):
        self._patch_get({"id": 1, "title": "foo"})
        assert Project(id=1, title="foo") == await self.imp._fetch_project("bar")
        self._assert_get("account/projects/bar")

    async def test_fetch_article(self):
        self._patch_get({"id": 1, "title": "foo"})
        assert Article(id=1, title="foo") == await self.imp._fetch_article("bar")
        self._assert_get("account/articles/bar")

    async def test_fetch_file(self):
        self._patch_get({"id": 1, "name": "foo"})
        assert File(id=1, name="foo", article_id=321) == await self.imp._fetch_file(
            321, 123
        )
        self._assert_get("account/articles/321/files/123")
