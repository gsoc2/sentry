import {Fragment, useMemo} from 'react';
import {RouteComponentProps} from 'react-router';
import styled from '@emotion/styled';

import Access from 'sentry/components/acl/access';
import {Button} from 'sentry/components/button';
import Confirm from 'sentry/components/confirm';
import EmptyMessage from 'sentry/components/emptyMessage';
import ExternalLink from 'sentry/components/links/externalLink';
import LoadingIndicator from 'sentry/components/loadingIndicator';
import Panel from 'sentry/components/panels/panel';
import PanelBody from 'sentry/components/panels/panelBody';
import PanelHeader from 'sentry/components/panels/panelHeader';
import PanelItem from 'sentry/components/panels/panelItem';
import SentryDocumentTitle from 'sentry/components/sentryDocumentTitle';
import {IconDelete} from 'sentry/icons';
import {t, tct} from 'sentry/locale';
import {space} from 'sentry/styles/space';
import {TagWithTopValues} from 'sentry/types';
import {setApiQueryData, useApiQuery, useQueryClient} from 'sentry/utils/queryClient';
import routeTitleGen from 'sentry/utils/routeTitle';
import useApi from 'sentry/utils/useApi';
import useOrganization from 'sentry/utils/useOrganization';
import useProjects from 'sentry/utils/useProjects';
import SettingsPageHeader from 'sentry/views/settings/components/settingsPageHeader';
import TextBlock from 'sentry/views/settings/components/text/textBlock';
import PermissionAlert from 'sentry/views/settings/project/permissionAlert';

type Props = RouteComponentProps<{projectId: string}, {}>;

function ProjectTags(props: Props) {
  const organization = useOrganization();
  const {projects} = useProjects();
  const projectId = props.params.projectId;

  const project = useMemo(
    () => projects.find(p => p.id === projectId),
    [projects, projectId]
  );

  const api = useApi();
  const queryClient = useQueryClient();

  const {data: tags, isLoading} = useApiQuery<TagWithTopValues[]>(
    [`/projects/${organization.slug}/${projectId}/tags/`],
    {staleTime: 0}
  );

  function handleDelete(key: TagWithTopValues['key']) {
    api.requestPromise(`/projects/${organization.slug}/${projectId}/tags/${key}/`, {
      method: 'DELETE',
    });

    setApiQueryData<TagWithTopValues[]>(
      queryClient,
      [`/projects/${organization.slug}/${projectId}/tags/`],
      oldTags => oldTags.filter(tag => tag.key !== key)
    );
  }
  if (isLoading) {
    return <LoadingIndicator />;
  }

  const isEmpty = !tags || !tags.length;
  return (
    <Fragment>
      <SentryDocumentTitle title={routeTitleGen(t('Tags'), projectId, false)} />
      <SettingsPageHeader title={t('Tags')} />
      <TextBlock>
        {tct(
          `Each event in Sentry may be annotated with various tags (key and value pairs).
                 Learn how to [link:add custom tags].`,
          {
            link: (
              <ExternalLink href="https://docs.sentry.io/platform-redirect/?next=/enriching-events/tags/" />
            ),
          }
        )}
      </TextBlock>

      <PermissionAlert project={project} />
      <Panel>
        <PanelHeader>{t('Tags')}</PanelHeader>
        <PanelBody>
          {isEmpty ? (
            <EmptyMessage>
              {tct('There are no tags, [link:learn how to add tags]', {
                link: (
                  <ExternalLink href="https://docs.sentry.io/product/sentry-basics/enrich-data/" />
                ),
              })}
            </EmptyMessage>
          ) : (
            <Access access={['project:write']} project={project}>
              {({hasAccess}) =>
                tags.map(({key, canDelete}) => {
                  const enabled = canDelete && hasAccess;
                  return (
                    <TagPanelItem key={key} data-test-id="tag-row">
                      <TagName>{key}</TagName>
                      <Actions>
                        <Confirm
                          message={t('Are you sure you want to remove this tag?')}
                          onConfirm={() => handleDelete(key)}
                          disabled={!enabled}
                        >
                          <Button
                            size="xs"
                            title={
                              enabled
                                ? t('Remove tag')
                                : hasAccess
                                ? t('This tag cannot be deleted.')
                                : t('You do not have permission to remove tags.')
                            }
                            aria-label={t('Remove tag')}
                            icon={<IconDelete size="xs" />}
                            data-test-id="delete"
                          />
                        </Confirm>
                      </Actions>
                    </TagPanelItem>
                  );
                })
              }
            </Access>
          )}
        </PanelBody>
      </Panel>
    </Fragment>
  );
}

export default ProjectTags;

const TagPanelItem = styled(PanelItem)`
  padding: 0;
  align-items: center;
`;

const TagName = styled('div')`
  flex: 1;
  padding: ${space(2)};
`;

const Actions = styled('div')`
  display: flex;
  align-items: center;
  padding: ${space(2)};
`;
