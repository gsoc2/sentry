import {Fragment, ReactNode, useMemo} from 'react';
import first from 'lodash/first';

import ReplayCountContext from 'sentry/components/replays/replayCountContext';
import useReplaysCount from 'sentry/components/replays/useReplaysCount';
import GroupStore from 'sentry/stores/groupStore';
import type {Group, Organization} from 'sentry/types';
import projectSupportsReplay from 'sentry/utils/replays/projectSupportsReplay';
import useOrganization from 'sentry/utils/useOrganization';

type Props = {
  children: ReactNode;
  groupIds: string[];
};

/**
 * Component to make it easier to query for replay counts against a list of groups
 * that exist across many projects.
 *
 * Later on when you want to read the fetched data:
 * ```
 * import ReplayCountContext from 'sentry/components/replays/replayCountContext';
 * const count = useContext(ReplayCountContext)[groupId];
 * ```
 */
export default function IssuesReplayCountProvider({children, groupIds}: Props) {
  const organization = useOrganization();
  const hasSessionReplay = organization.features.includes('session-replay-ui');

  if (hasSessionReplay) {
    return (
      <Provider organization={organization} groupIds={groupIds}>
        {children}
      </Provider>
    );
  }

  return <Fragment>{children}</Fragment>;
}

function Provider({
  children,
  groupIds,
  organization,
}: Props & {organization: Organization}) {
  // Only ask for the groupIds where the project supports replay.
  // For projects that don't support replay the count will always be zero.
  const groups = useMemo(
    () =>
      groupIds
        .map(id => GroupStore.get(id) as Group)
        .filter(Boolean)
        .filter(group => projectSupportsReplay(group.project)),
    [groupIds]
  );

  // Any project that supports replay will do here.
  // Project is used to signal if we should/should not do the query at all.
  const project = first(groups)?.project;

  const counts = useReplaysCount({
    groupIds,
    organization,
    projectIds: project ? [Number(project.id)] : [],
  });

  return (
    <ReplayCountContext.Provider value={counts}>{children}</ReplayCountContext.Provider>
  );
}
