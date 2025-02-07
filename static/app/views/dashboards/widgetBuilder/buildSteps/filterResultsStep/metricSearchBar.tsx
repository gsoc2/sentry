import styled from '@emotion/styled';

import {PageFilters} from 'sentry/types';
import {parseMRI} from 'sentry/utils/metrics';
import {WidgetQuery} from 'sentry/views/dashboards/types';
import {MetricSearchBar as DDMSearchBar} from 'sentry/views/ddm/queryBuilder';

interface Props {
  pageFilters: PageFilters;
  widgetQuery: WidgetQuery;
}

export function MetricSearchBar({pageFilters, widgetQuery}: Props) {
  const projectIds = pageFilters.projects;
  const {mri} = parseMRI(widgetQuery.aggregates[0]) ?? {};

  return (
    <SearchBar
      // TODO(aknaus): clean up projectId type in ddm
      projectIds={projectIds.map(id => id.toString())}
      mri={mri}
      disabled={!mri}
      query={widgetQuery.conditions}
      onChange={() => {}}
    />
  );
}

const SearchBar = styled(DDMSearchBar)`
  flex-grow: 1;
`;
