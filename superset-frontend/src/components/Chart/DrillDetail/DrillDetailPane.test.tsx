/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import fetchMock from 'fetch-mock';
import {
  GenericDataType,
  QueryFormData,
  SupersetClient,
} from '@superset-ui/core';
import userEvent from '@testing-library/user-event';
import { render, screen, waitFor } from 'spec/helpers/testing-library';
import { getMockStoreWithNativeFilters } from 'spec/fixtures/mockStore';
import chartQueries, { sliceId } from 'spec/fixtures/mockChartQueries';
import { supersetGetCache } from 'src/utils/cachedSupersetGet';
import DrillDetailPane from './DrillDetailPane';
import { buildSearchFilters } from './DrillDetailColumnFilters';

const chart = chartQueries[sliceId];
const setup = (overrides: Record<string, any> = {}) => {
  const store = getMockStoreWithNativeFilters();
  const props = {
    initialFilters: [],
    formData: chart.form_data as unknown as QueryFormData,
    ...overrides,
  };
  return render(<DrillDetailPane {...props} />, {
    useRedux: true,
    store,
  });
};

const waitForRender = (overrides: Record<string, any> = {}) =>
  waitFor(() => setup(overrides));

const SAMPLES_ENDPOINT =
  'glob:*/datasource/samples?force=false&datasource_type=table&datasource_id=7&per_page=*&page=1';

const DATASET_ENDPOINT = 'glob:*/api/v1/dataset/*';

const MOCKED_DATASET = {
  changed_on_humanized: '2 days ago',
  created_on_humanized: 'a week ago',
  description: 'Simple description',
  table_name: 'test_table',
  changed_by: {
    first_name: 'John',
    last_name: 'Doe',
  },
  created_by: {
    first_name: 'John',
    last_name: 'Doe',
  },
  owners: [
    {
      first_name: 'John',
      last_name: 'Doe',
    },
  ],
};

const setupDatasetEndpoint = () => {
  fetchMock.get(DATASET_ENDPOINT, {
    status: 'complete',
    result: MOCKED_DATASET,
  });
};

const fetchWithNoData = () => {
  setupDatasetEndpoint();
  fetchMock.post(SAMPLES_ENDPOINT, {
    result: {
      total_count: 0,
      data: [],
      colnames: [],
      coltypes: [],
    },
  });
};

const fetchWithData = () => {
  setupDatasetEndpoint();
  fetchMock.post(SAMPLES_ENDPOINT, {
    result: {
      total_count: 3,
      data: [
        {
          year: 1996,
          na_sales: 11.27,
          eu_sales: 8.89,
        },
        {
          year: 1989,
          na_sales: 23.2,
          eu_sales: 2.26,
        },
        {
          year: 1999,
          na_sales: 9,
          eu_sales: 6.18,
        },
      ],
      colnames: ['year', 'na_sales', 'eu_sales'],
      coltypes: [0, 0, 0],
    },
  });
};

afterEach(() => {
  fetchMock.restore();
  supersetGetCache.clear();
});

test('should render', async () => {
  fetchWithNoData();
  const { container } = await waitForRender();
  expect(container).toBeInTheDocument();
});

test('should render loading indicator', async () => {
  fetchWithData();
  setup();
  await waitFor(() =>
    expect(screen.getByLabelText('Loading')).toBeInTheDocument(),
  );
});

test('should render the table with results', async () => {
  fetchWithData();
  await waitForRender();
  expect(screen.getByRole('table')).toBeInTheDocument();
  expect(screen.getByText('1996')).toBeInTheDocument();
  expect(screen.getByText('11.27')).toBeInTheDocument();
  expect(screen.getByText('1989')).toBeInTheDocument();
  expect(screen.getByText('23.2')).toBeInTheDocument();
  expect(screen.getByText('1999')).toBeInTheDocument();
  expect(screen.getByText('9')).toBeInTheDocument();
  expect(
    screen.getByRole('columnheader', { name: /^year/ }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole('columnheader', { name: /^na_sales/ }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole('columnheader', { name: /^eu_sales/ }),
  ).toBeInTheDocument();
});

test('should render the "No results" components', async () => {
  fetchWithNoData();
  setup();
  expect(
    await screen.findByText('No rows were returned for this dataset'),
  ).toBeInTheDocument();
});

test('should render the metadata bar', async () => {
  fetchWithNoData();
  setup();
  expect(
    await screen.findByText(MOCKED_DATASET.table_name),
  ).toBeInTheDocument();
  expect(
    await screen.findByText(MOCKED_DATASET.description),
  ).toBeInTheDocument();
  expect(
    await screen.findByText(
      `${MOCKED_DATASET.created_by.first_name} ${MOCKED_DATASET.created_by.last_name}`,
    ),
  ).toBeInTheDocument();
  expect(
    await screen.findByText(MOCKED_DATASET.changed_on_humanized),
  ).toBeInTheDocument();
});

test('should render an error message when fails to load the metadata', async () => {
  fetchWithNoData();
  fetchMock.get(DATASET_ENDPOINT, { status: 400 }, { overwriteRoutes: true });
  setup();
  expect(
    await screen.findByText('There was an error loading the dataset metadata'),
  ).toBeInTheDocument();
});

const NA_SALES = ['9', '11.27', '23.2'];
const naSalesOrder = () =>
  Array.from(document.querySelectorAll('.virtual-table-cell'))
    .map(cell => cell.textContent)
    .filter(text => NA_SALES.includes(text as string));

test('should sort the whole result by clicking a column header', async () => {
  fetchWithData();
  await waitForRender();
  await screen.findByText('1996');
  userEvent.click(screen.getByRole('columnheader', { name: /^na_sales/ }));
  await waitFor(() => expect(naSalesOrder()).toEqual(['9', '11.27', '23.2']));
  userEvent.click(screen.getByRole('columnheader', { name: /^na_sales/ }));
  await waitFor(() => expect(naSalesOrder()).toEqual(['23.2', '11.27', '9']));
});

test('should search the loaded rows', async () => {
  fetchWithData();
  await waitForRender();
  await screen.findByText('1996');
  userEvent.type(screen.getByLabelText('Rechercher dans le tableau'), '1989');
  await waitFor(() =>
    expect(screen.queryByText('1996')).not.toBeInTheDocument(),
  );
  expect(screen.getByText('23.2')).toBeInTheDocument();
});

test('should send column filters to the server', async () => {
  fetchWithData();
  await waitForRender();
  await screen.findByText('1996');
  userEvent.click(screen.getByRole('button', { name: 'Filtrer par colonne' }));
  userEvent.type(screen.getByLabelText('na_sales'), '>10');
  await waitFor(
    () => {
      const calls = fetchMock.calls(SAMPLES_ENDPOINT);
      const body = JSON.parse(calls[calls.length - 1][1]?.body as string);
      expect(body.filters).toContainEqual({
        col: 'na_sales',
        op: '>',
        val: 10,
      });
    },
    { timeout: 3000 },
  );
});

test('should load every chunk so that search covers all rows', async () => {
  setupDatasetEndpoint();
  // the mock store sets SAMPLES_ROW_LIMIT to 10
  const rowsOf = (from: number, count: number) =>
    Array.from({ length: count }, (_, index) => ({
      mat_pers: `M${String(from + index).padStart(3, '0')}`,
    }));
  [rowsOf(0, 10), rowsOf(10, 10), rowsOf(20, 5)].forEach((data, index) =>
    fetchMock.post(`glob:*/datasource/samples?*per_page=10&page=${index + 1}`, {
      result: {
        total_count: 25,
        data,
        colnames: ['mat_pers'],
        coltypes: [1],
      },
    }),
  );
  await waitForRender();
  await screen.findByText('M000');
  userEvent.type(screen.getByLabelText('Rechercher dans le tableau'), 'M024');
  expect(await screen.findByText('M024')).toBeInTheDocument();
  expect(screen.queryByText('M000')).not.toBeInTheDocument();
});

test('buildSearchFilters parses text, numbers, dates and booleans', () => {
  const { filters, invalid } = buildSearchFilters(
    { name: 'tunis', age: '>=40', hired: '2020', active: 'oui', bad: 'abc' },
    ['name', 'age', 'hired', 'active', 'bad'],
    [
      GenericDataType.String,
      GenericDataType.Numeric,
      GenericDataType.Temporal,
      GenericDataType.Boolean,
      GenericDataType.Numeric,
    ],
  );
  expect(filters).toEqual([
    { col: 'name', op: 'ILIKE', val: '%tunis%' },
    { col: 'age', op: '>=', val: 40 },
    { col: 'hired', op: '>=', val: Date.UTC(2020, 0, 1) },
    { col: 'hired', op: '<', val: Date.UTC(2021, 0, 1) },
    { col: 'active', op: '==', val: true },
  ]);
  expect(invalid).toEqual(['bad']);
});

test('should render the error', async () => {
  jest
    .spyOn(SupersetClient, 'post')
    .mockRejectedValue(new Error('Something went wrong'));
  await waitForRender();
  expect(screen.getByText('Error: Something went wrong')).toBeInTheDocument();
});
