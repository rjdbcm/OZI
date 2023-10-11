# noqa: INP001
"""Unit and fuzz tests for ``ozi-new``."""
# Part of ozi.
# See LICENSE.txt in the project root for details.
import argparse
from itertools import zip_longest
import operator
import typing
from datetime import timedelta

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

import ozi.assets
import ozi.fix
import ozi.new


@settings(deadline=timedelta(milliseconds=500))
@given(
    project=st.fixed_dictionaries(
        {
            'verify_email': st.just(False),
            'strict': st.just(False),
            'target': st.data(),
            'keywords': st.from_regex(r'^([a-z_]*[a-z0-9],)*$'),
            'ci_provider': st.just('github'),
            'name': st.from_regex(r'^([A-Za-z]|[A-Za-z][A-Za-z0-9._-]*[A-Za-z0-9])$'),
            'author': st.text(min_size=1, max_size=248),
            'author_email': st.lists(st.emails()),
            'maintainer': st.text(min_size=1, max_size=248),
            'maintainer_email': st.lists(st.emails()),
            'homepage': st.one_of(st.just('https://oziproject.dev/')),
            'summary': st.text(max_size=512),
            'copyright_head': st.text(),
            'license_exception_id': st.one_of(
                list(map(st.just, ozi.new.CloseMatch.license_exception_id))
            ),
            'topic': st.one_of(list(map(st.just, ozi.new.CloseMatch.topic))),
            'audience': st.one_of(list(map(st.just, ozi.new.CloseMatch.audience))),
            'framework': st.one_of(list(map(st.just, ozi.new.CloseMatch.framework))),
            'environment': st.one_of(list(map(st.just, ozi.new.CloseMatch.environment))),
            'status': st.one_of(list(map(st.just, ozi.new.CloseMatch.status))),
        },
    ),
    license=st.data(),
    license_expression=st.data(),
    license_id=st.data(),
)
def test_fuzz_new_project_good_namespace(  # noqa: DC102
    tmp_path_factory: pytest.TempPathFactory,
    project: typing.Dict,
    license: typing.Any,
    license_id,
    license_expression,
) -> None:
    project['target'] = tmp_path_factory.mktemp('new_project_')
    project['license'] = license.draw(
        st.one_of(
            [
                st.just(k)
                for k, v in ozi.assets.spdx_options.items()
                if len(v) != 0 and k not in ['Private']
            ]
        )
    )
    project['license_id'] = license_id.draw(
        st.one_of(map(st.just, ozi.assets.spdx_options.get(project['license'])))  # type: ignore
    )
    project['license_expression'] = license_expression.draw(st.just(project['license_id']))
    assume(project['author_email'] != project['maintainer_email'])
    assume(len(project['author_email']))
    assume(
        map(
            operator.ne,
            *[
                i
                for i in zip_longest(project['author_email'], project['maintainer_email'])
                if any(i)
            ],
        )
    )
    assume(project['author'] != project['maintainer'])
    namespace = argparse.Namespace(**project)
    ozi.new.new_project(project=namespace)


@pytest.mark.parametrize(
    'item',
    [
        {'ci_provider': ''},
        {'summary': 'A' * 513},
        {'name': '➿'},
        {
            'license': 'DFSG approved',
            'license_expression': 'Private',
            'license_id': 'Private',
        },
        {'author_email': ['foobarbademail']},
        {
            'author_email': ['noreply@oziproject.dev'],
            'maintainer_email': ['noreply@oziproject.dev'],
        },
        {
            'author_email': [],
            'maintainer_email': ['noreply@oziproject.dev'],
        },
        {
            'author': '',
            'maintainer': 'foo',
        },
        {
            'author': 'Zaphod Beeblebrox',
            'maintainer': '',
            'author_email': ['noreply@oziproject.dev'],
            'maintainer_email': ['user@example.com'],
        },
    ],
)
def test_new_project_bad_args(  # noqa: DC102
    item: dict,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    project_dict = {
        'verify_email': False,
        'strict': False,
        'target': tmp_path_factory.mktemp('new_project_bad_args'),
        'ci_provider': 'github',
        'name': 'ozi.phony',
        'license': 'CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',
        'author': 'Ross J. Duff',
        'author_email': ['noreply@oziproject.dev'],
        'keywords': '',
        'maintainer': '',
        'maintainer_email': [],
        'homepage': 'https://oziproject.dev/',
        'summary': '',
        'copyright_head': '',
        'license_expression': 'CC0-1.0',
        'license_id': 'CC0-1.0',
        'license_exception_id': '',
        'topic': 'Utilities',
        'audience': 'Developers',
        'framework': 'Pytest',
        'environment': 'No Input/Output (Daemon)',
        'status': '1 - Planning',
    }
    project_dict.update(item)
    namespace = argparse.Namespace(**project_dict)
    with pytest.warns(RuntimeWarning):
        ozi.new.new_project(project=namespace)


def test_new_project_bad_target_not_empty(  # noqa: DC102
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    project_dict = {
        'verify_email': False,
        'strict': False,
        'target': tmp_path_factory.mktemp('new_project_target_not_empty'),
        'ci_provider': 'github',
        'name': 'ozi.phony',
        'license': '',
        'keywords': '',
        'author': 'Ross J. Duff',
        'author_email': ['noreply@oziproject.dev'],
        'maintainer': '',
        'maintainer_email': [],
        'homepage': 'https://oziproject.dev/',
        'summary': '',
        'copyright_head': '',
        'license_expression': 'CC0-1.0',
        'license_id': 'CC0-1.0',
        'license_exception_id': '',
        'topic': 'Utilities',
        'audience': 'Developers',
        'framework': 'Pytest',
        'environment': 'No Input/Output (Daemon)',
        'status': '1 - Planning',
    }
    (project_dict['target'] / 'foobar').touch()
    namespace = argparse.Namespace(**project_dict)
    with pytest.warns(RuntimeWarning):
        ozi.new.new_project(project=namespace)


@given(
    option_strings=st.lists(st.from_regex(r'--[a-z]*-?[a-z*]')),
    dest=st.text(),
    nargs=st.one_of(st.none(), st.text()),
    data=st.one_of(
        st.just('license'),
        st.just('environment'),
        st.just('framework'),
        st.just('license-id'),
        st.just('license-exception-id'),
        st.just('audience'),
        st.just('language'),
        st.just('topic'),
        st.just('status'),
        st.none(),
    ),
)
def test_fuzz_CloseMatch(  # noqa: DC102
    option_strings: typing.List[str],
    dest: str,
    nargs: typing.Union[int, str, None],
    data: typing.Any,
) -> None:
    if nargs is not None:
        with pytest.raises(ValueError, match='nargs not allowed'):
            ozi.new.CloseMatch(option_strings=option_strings, dest=dest, nargs=nargs)
    else:
        close_match = ozi.new.CloseMatch(
            option_strings=option_strings, dest=dest, nargs=nargs
        )
        if data not in [None, 'topic', 'status']:
            close_match(argparse.ArgumentParser(), argparse.Namespace(), data, f'--{data}')
        else:
            with pytest.warns(RuntimeWarning):
                close_match(
                    argparse.ArgumentParser(),
                    argparse.Namespace(),
                    data,
                    f'--{data}' if data is not None else None,
                )


@given(
    msg=st.text(),
    category=st.just(Warning),
    filename=st.text(),
    lineno=st.integers(),
    line=st.one_of(st.none(), st.text()),
)
def test_fuzz_tap_warning_format(  # noqa: DC102
    msg: str, category: type, filename: str, lineno: int, line: typing.Optional[str]
) -> None:
    ozi.new.tap_warning_format(
        msg=msg, category=category, filename=filename, lineno=lineno, line=line
    )
