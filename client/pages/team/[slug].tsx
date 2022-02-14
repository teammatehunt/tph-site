import React, { useState, useRef } from 'react';
import Head from 'next/head';
import { GetServerSideProps } from 'next';
import { ParsedUrlQuery } from 'querystring';
import { useRouter } from 'next/router';

import { DjangoFormErrors, DjangoFormResponse } from 'types';
import { clientFetch, serverFetch } from 'utils/fetch';
import { formattedDateTime, displayTimeLeft } from 'utils/timer';

import HuntEmail from 'components/hunt_email';
import Section from 'components/section';
import { FullTable } from 'components/table';
import Title from 'components/title';
import {
  TeamMember,
  TeamMemberFields,
  TeamMembersForm,
} from 'components/register';
import StoryNotifications from 'components/story_notifications';
import Link from 'next/link';
import LinkIfStatic from 'components/link';

interface SolveInfo {
  slug: string;
  name: string;
  is_meta: boolean;
  unlock_time: string;
  solve_time: string;
  open_duration: number;
  guesses: number;
}

interface Props {
  teamInfo?: {
    name: string;
    slug: string;
    profile_pic?: string;
    profile_pic_approved: boolean;
    members: TeamMember[];
  };
  submissions?: SolveInfo[];
  canModify: boolean;
}

interface ProfilePicForm {
  profile_pic?: string;
}

// This is different from the standard DjangoFormResponse because
// some images are valid even when there are form errors.
interface Response {
  form_errors?: DjangoFormErrors<ProfilePicForm>;
  profile_pic?: string;
  is_valid: boolean;
}

const EditProfilePicForm = ({
  teamSlug,
  profilePic,
  setProfilePic,
  setProfilePicApproved,
}) => {
  const router = useRouter();
  const [errors, setErrors] = useState<DjangoFormErrors<ProfilePicForm>>({});
  const [status, setStatus] = useState<number>(200);
  const [isUploading, setUploading] = useState<boolean>(false);
  const [sentRequest, setSentRequest] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const onSubmit = async (e) => {
    e.preventDefault();
    setUploading(true);
    setErrors({});
    const data = new FormData(e.target);
    // If it is null, let request go to server, server will reply with correct
    // error message.
    if (fileInputRef.current?.files) {
      const file = fileInputRef.current.files[0];
      const max_file_size = 20971520; // 20 MB
      // don't send the request, give back a fake response and stop right away.
      if (file.size > max_file_size) {
        setSentRequest(true);
        setStatus(400);
        const errorMessage =
          'The uploaded file was too large. The maximum file size is 20 MB.';
        setErrors({ profile_pic: errorMessage });
        return;
      }
    }
    const response = await clientFetch<Response>(
      router,
      `/upload_profile_pic/${teamSlug}`,
      {
        method: 'POST',
        body: data,
      }
    );

    if (response != null) {
      setStatus(response.statusCode);
      setSentRequest(true);
    }
    if (response?.form_errors) {
      setErrors(response.form_errors);
    }
    if (response.statusCode === 200 && response.profile_pic) {
      // valid team photo, but not approved yet.
      setProfilePic(response.profile_pic);
      setProfilePicApproved(false);
    }
    setUploading(false);
  };

  const onClickDelete = async (e) => {
    e.preventDefault();
    const response = await clientFetch<Response>(
      router,
      `/delete_profile_pic/${teamSlug}`,
      {
        method: 'POST',
      }
    );
    if (response != null) {
      setStatus(response.statusCode);
      if (response.statusCode === 200) {
        // reset everything.
        setErrors({});
        setProfilePic('');
        setProfilePicApproved(false);
        setUploading(false);
        setSentRequest(false);
      }
    }
  };

  return (
    <>
      <p className="small">
        (Optional) Please upload a public team photo (e.g. photo, pictures, or a
        meme).
      </p>
      <p className="small">
        <strong>
          Since this photo will be viewable by all guests, it will need to go
          through a short approval process.
        </strong>{' '}
        Be patient if it isn’t immediately public.
      </p>
      <p className="small">
        Photos should be of file type JPEG or PNG, and can be at most 1280
        pixels x 720 pixels.
      </p>
      <form
        className="flex-center-vert"
        encType="multipart/form-data"
        method="post"
        onSubmit={onSubmit}
      >
        <input
          ref={fileInputRef}
          name="profile_pic"
          type="file"
          disabled={isUploading}
          required
        />
        <input
          type="submit"
          disabled={isUploading}
          value={isUploading ? 'Uploading...' : 'Upload'}
        />
      </form>
      {profilePic && (
        <>
          <span className="delet">Delete team photo?</span>
          <input type="submit" onClick={onClickDelete} value="Delete" />
        </>
      )}
      {sentRequest && status !== 200 && (
        <>
          <p className="formerror">
            ERROR: {errors.profile_pic} If you did not expect to see this,
            please contact us at <HuntEmail />.
          </p>
        </>
      )}
      <style jsx>{`
        form {
          align-items: stretch;
          margin-bottom: 14px;
        }

        .delet {
          margin-right: 12px;
        }

        input {
          font-size: 16px;
          padding: 4px 8px;
        }

        .small {
          font-size: 14px;
        }
      `}</style>
    </>
  );
};

const EditTeamMembersForm = ({ teamInfo }) => {
  const router = useRouter();
  const [errors, setErrors] = useState<DjangoFormErrors<TeamMembersForm>>({});
  const [serverError, setServerError] = useState<boolean>(false);
  const [isSaving, setSaving] = useState<boolean>(false);
  const [isSuccess, setSuccess] = useState<boolean>(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    setSaving(true);
    setSuccess(false);
    setErrors({});
    setServerError(false);
    const response = await clientFetch<
      DjangoFormResponse<TeamMembersForm, void>
    >(router, `/team_info/${teamInfo.slug}/edit`, {
      method: 'POST',
      body: data,
    });

    if (response?.form_errors) {
      setErrors(response.form_errors);
    } else if (response === undefined || response.statusCode !== 200) {
      // something crazy happened, ask them to explain what they did.
      setServerError(true);
    } else {
      setSuccess(true);
    }
    setSaving(false);
  };

  return (
    <>
      <form onSubmit={onSubmit}>
        {isSuccess && <p>Teammates updated!</p>}
        {serverError && (
          <p className="error">
            Something unexpected happened when updating team members. Please
            contact us and we will fix it!
          </p>
        )}
        <TeamMemberFields members={teamInfo.members} errors={errors} />
        <input
          type="submit"
          disabled={isSaving}
          value={isSaving ? 'Updating teammates...' : 'Update teammates'}
        />
      </form>

      <style jsx>{`
        input {
          font-size: 16px;
          margin-top: 2em;
          padding: 4px 8px;
        }
      `}</style>
    </>
  );
};

const SolveStats = ({ submissions }) => {
  if (!submissions) {
    return <></>;
  }
  if (submissions.length === 0) {
    return <></>;
  }
  return (
    <>
      <FullTable>
        <thead>
          <tr>
            <th>Puzzle</th>
            <th>Wrong guesses</th>
            <th>Unlock time</th>
            <th>Time to solve</th>
            <th>Solve time</th>
          </tr>
        </thead>
        <tbody>
          {submissions.map((solve, i) => {
            const puzzlelink = (
              <LinkIfStatic href={`/puzzles/${solve.slug}`}>
                {solve.name}
              </LinkIfStatic>
            );
            return (
              <tr>
                <td>
                  {solve.is_meta ? <strong>{puzzlelink}</strong> : puzzlelink}
                </td>
                <td>{solve.guesses}</td>
                <td>
                  {formattedDateTime(solve.unlock_time, {
                    year: undefined,
                    weekday: undefined,
                  })}
                </td>
                <td>
                  {displayTimeLeft(solve.open_duration, 1, {
                    showHours: true,
                    showDays: false,
                    verbose: true,
                    warningAt: 0,
                  })}
                </td>
                <td>
                  {formattedDateTime(solve.solve_time, {
                    year: undefined,
                    weekday: undefined,
                  })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </FullTable>
      <style jsx>{`
        th {
          font-size: 24px;
          padding-bottom: 4px;
          padding-right: 4px;
          word-wrap: anywhere;
        }
        td {
          padding-top: 4px;
          padding-bottom: 4px;
          padding-right: 4px;
          word-wrap: anywhere;
        }
        th,
        tr {
          border-bottom: 1px dashed black;
        }
      `}</style>
    </>
  );
};

const TeamPage = ({ teamInfo, submissions, canModify }: Props) => {
  if (!teamInfo) {
    return (
      <>
        <Title title="Team not found" />
        <StoryNotifications onlyFinished />
        <Section>
          <p>That team could not be found.</p>
        </Section>
      </>
    );
  }

  const [profilePic, setProfilePic] = useState<string>(
    teamInfo.profile_pic || ''
  );
  const [profilePicApproved, setProfilePicApproved] = useState<boolean>(
    teamInfo.profile_pic_approved
  );

  return (
    <>
      {profilePic && profilePicApproved && (
        <Head>
          <meta
            key="og-image"
            property="og:image"
            content={
              // Must be an absolute URL.
              `https://${process.env.domainName}/${profilePic}`
            }
          />
        </Head>
      )}

      <Title title={teamInfo.name} />
      <div className="center">
        <Section>
          {profilePic && canModify && !profilePicApproved && (
            <p>
              Your team photo is under review. If approved, it will look like
              this.
            </p>
          )}
          {profilePic && canModify && profilePicApproved && (
            <p>Your team photo is approved!</p>
          )}
          {profilePic && (canModify || profilePicApproved) && (
            <img src={profilePic} />
          )}
          {canModify && (
            <EditProfilePicForm
              teamSlug={teamInfo.slug}
              profilePic={profilePic}
              setProfilePic={setProfilePic}
              setProfilePicApproved={setProfilePicApproved}
            />
          )}
        </Section>
        <Section heading="teammates">
          {canModify ? (
            <EditTeamMembersForm teamInfo={teamInfo} />
          ) : (
            <ul>
              {teamInfo.members.map((member) => (
                <li key={member.name}>{member.name}</li>
              ))}
            </ul>
          )}
        </Section>
      </div>
      {submissions && (
        <Section>
          <SolveStats submissions={submissions} />
        </Section>
      )}

      <style jsx>{`
        img {
          max-height: 40vh;
        }

        ul {
          margin: 0 auto;
          max-width: 500px;
          padding: 0;
        }

        li {
          list-style: none;
        }
      `}</style>
    </>
  );
};

export default TeamPage;

interface UrlParams extends ParsedUrlQuery {
  slug: string;
}

export const getServerSideProps = async (context) => {
  const { params } = context;
  const { slug } = params || {};
  let resp: Props;
  if (process.env.isStatic) {
    resp = require(`assets/json_responses/team/${slug}.json`);
  } else {
    resp = await serverFetch<Props>(context, `/team_info/${slug || ''}`, {
      method: 'GET',
    });
  }
  return { props: resp };
};

/*
export const getStaticPaths = async () => {
  return require('assets/json_responses/team_paths.json');
};
*/
