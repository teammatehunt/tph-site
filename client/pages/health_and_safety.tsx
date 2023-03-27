/**
 * This file is adapted from previous Health & Safety docs for MH 2023.
 * If you are running a MH, you'll want to consult with puzzle club to update this.
 * If you are not running a MH, you can delete this file.
 */
import React, { useContext } from 'react';

import Section from 'components/section';

const HQ_EMAIL = 'info@FIXME';

const HealthAndSafety = () => {
  return (
    <>
      <Section title="Health & Safety">
        <div id="content">
          <p>
            Ensuring the health and safety of all Mystery Hunt participants is a
            top priority. As the leaders of your teams, you are primarily
            responsible for handling emergencies and for ensuring the overall
            health and safety of team members (or designating a responsible team
            member for that role).
          </p>
          <p>
            This document contains important information and helpful tips. Read
            it, learn it, share it, live it.
          </p>
          <Section heading="Use Common Sense">
            <ul>
              <li>
                This is a puzzle-solving competition, not a mountain-climbing
                expedition. There is no reason for anyone to put themselves at
                risk of being harmed, arrested, or held liable for any property
                damage. Our actions will also reflect on the Mystery Hunt as a
                whole, so let's stay safe and responsible both for our own sakes
                and for the sake of everyone who loves the Mystery Hunt and
                cares about its future.
              </li>
              <li>
                <b>Follow our instructions.</b> During hunt, we will communicate
                any important health and safety information on the hunt website,
                by e-mail, by phone, and in person if needed.
              </li>
              <li>
                One volunteer on each team should be designated as the{' '}
                <b>“Health &amp; Safety Marshal”</b>. That person should be
                familiar with the information in these guidelines and ready to
                respond if a problem arises while your team is hunting.
              </li>
              <li>
                <b>
                  If you think you are about to do something illegal, unsafe,
                  against MIT policy or otherwise ill-advised, CALL HUNT HQ
                  FIRST.
                </b>
              </li>
            </ul>
          </Section>
          <Section heading="Important Contact Information">
            <ul>
              <li>
                <b>MIT Police: &nbsp;617-253-1212</b> (or 100 from a campus
                phone). The MIT Police should be contacted in all emergencies,
                whether they are of a criminal, medical, or safety nature, or to
                report an encounter with a suspicious or dangerous person who is
                not participating in the hunt. The MIT Police will dispatch the
                appropriate resources, which in some cases might include the
                student-run MIT-EMS, who will have an ambulance on call.
              </li>
              <li>
                <b>Hunt HQ Phone: &nbsp;617-324-7732.</b> &nbsp;Call during hunt
                if you encounter a “real-life situation” and you do not know
                what to do (minor medical issue, lost team member, encounter
                with police, damage to MIT property, etc.).
              </li>
              <li>
                <b>Hunt Organizers E-mail: &nbsp;{HQ_EMAIL}.</b> All incidents
                should be reported by e-mail after the immediate emergency or
                threat has been managed.
              </li>
            </ul>
          </Section>
          <Section heading="Alerts">
            <ul>
              <li>
                <b>MIT Alert System:&nbsp;</b> Provides real-time alerts for
                emergencies on campus. We will add at least one contact per team
                just for Hunt weekend (via the Health &amp; Safety Quiz); to
                subscribe permanently, visit{' '}
                <a href="http://em2.mit.edu/mitalert/">
                  http://em2.mit.edu/mitalert/
                </a>
                .
              </li>
              <li>
                <b>Fire Alarms:&nbsp;</b> If an alarm sounds, do not continue
                working. All team members must immediately exit the building
                through the nearest marked exit, and wait for further
                instructions.
              </li>
            </ul>
          </Section>
          <Section heading="Medical Care">
            <ul>
              <li>
                <b>Urgent Care:</b>
                <ul>
                  <li>
                    <b>MIT affiliates</b> can use MIT Medical’s Urgent Care in
                    building E23 for non-emergency treatment, 10 AM–4 PM.
                    Overnight, call MIT Medical at 617-253-4481 to speak with a
                    nurse, who can schedule a next-day appointment.
                  </li>
                  <li>
                    Non-MIT affiliates <b>should not</b> use MIT’s Urgent Care
                    service, Instead, use area hospitals for urgent medical
                    needs. Massachusetts General Hospital, Cambridge Hospital,
                    and Mount Auburn Hospital are the closest.
                  </li>
                </ul>
              </li>
              <li>
                <b>First Aid:&nbsp;</b> Hunt HQ will provide a kit to each team
                for treating minor issues.
              </li>
            </ul>
          </Section>
          <Section heading="Know Where You Are">
            <ul>
              <li>
                <b>MIT is a real university</b>, and Mystery Hunt is not the
                only thing happening. Try not to disturb researchers, staff, and
                other activities that might be occurring on campus.
              </li>
              <li>
                <b>Don’t go anywhere or do anything illegal or unsafe.</b>{' '}
                Mystery Hunt takes place in specified rooms and campus locations
                accessible to the MIT community at large. Don’t attempt to enter
                other spaces, except locations where events are scheduled or
                that Hunt personnel explicitly provide access to. Don’t force
                open locked doors or set off emergency alarms.
              </li>
              <li>
                <b>
                  Don’t carry any weapon, or anything that looks like a weapon,
                  on campus.
                </b>
              </li>
              <li>
                <b>Be careful with MIT property</b>, especially if your team is
                using an MIT room as its base. Damage to property will reflect
                poorly on the Mystery Hunt in general and will compromise your
                team’s ability to use MIT rooms in the future.
              </li>
              <li>
                <b>Team members may not know MIT’s campus well.</b> Before
                sending team members on an excursion, you should ensure you can
                stay in touch with them (and vice versa). If needed, provide
                team members with maps.{' '}
                <a href="http://whereis.mit.edu">Whereis</a> and the{' '}
                <a href="http://m.mit.edu">MIT mobile website</a> both have
                campus maps.
              </li>
              <li>
                <b>If you think a team member is lost</b>, call them directly.
                If that fails, call Hunt HQ, and if we cannot help, contact MIT
                Police.
              </li>
            </ul>
          </Section>
          <Section heading="Stay Healthy">
            <ul>
              <li>
                Ask if any of your team members have{' '}
                <b>allergies or other health conditions</b> that might require
                attention, and take appropriate precautions.
              </li>
              <li>
                Make sure every team member has a <b>plan for getting sleep</b>.
                &nbsp;“Work until burnout” is not a winning strategy. Getting
                sleep is important — Mystery Hunt is a marathon, not a sprint.
                <ul>
                  <li>
                    <b>
                      MIT rules do not allow sleeping in classrooms, lounges,
                      hallways, etc.
                    </b>{' '}
                    Make appropriate arrangements so that team members can sleep
                    in dorms, hotels or nearby residences. Dorm residents
                    hosting hunters should adhere to the guest policies of their
                    residence halls.
                  </li>
                  <li>
                    <b>
                      MIT does not allow visitors to access campus between 1 AM
                      and 6 AM.
                    </b>{' '}
                    Students who live on campus should stay in dorms and not
                    access other campus buildings during this time.
                  </li>
                </ul>
              </li>
              <li>
                Be sure team members <b>stay hydrated</b> and have{' '}
                <b>nutritious food</b> to eat over the course of the weekend.
                Not just Oreos and Mountain Dew. There are food options
                available nearby in Kendall Square, Central Square, and the MIT
                Student Center.
              </li>
              <li>
                <b>No alcohol or drugs</b> on campus. Possession or consumption
                of alcohol or drugs in classrooms or in public MIT campus spaces
                (except pubs) is strictly prohibited. This policy applies even
                if everyone on your team is of legal drinking age.
              </li>
            </ul>
          </Section>
          <Section heading="Minors">
            <ul>
              <li>
                Minors may attend or participate in Mystery Hunt from on-campus
                locations between the hours of 6:00 AM and 1:00 AM.
              </li>
              <li>
                <b>
                  Minors must be accompanied by a parent/guardian at all times
                </b>
                .
              </li>
              <li>
                Minors are not permitted to attend live kickoff/wrapup, attend
                in-person event puzzles, or work on field puzzles. Minors are
                permitted to work on online puzzles from their team classroom.
              </li>
              <li>
                Minors must travel to and from campus with their
                parent/guardian.
              </li>
              <li>
                If you need to interact with an unsupervised minor, have another
                adult present and conduct those interactions in a public
                environment where you can be observed.
              </li>
              <li>
                The full{' '}
                <a href="https://docs.google.com/document/d/1SUdGC5DV97YKieOd8TwNV_d1HiIoqlWQ4P2EcI4wTcA/edit">
                  Regulations Regarding the Presence and Participation of Minors
                </a>{' '}
                should be reviewed by every team captain, along with the{' '}
                <a href="https://drive.google.com/file/d/1a6Q0c-gml2rXjrLzrj7ZAk78_t-LRP2I/view">
                  MIT Code of Conduct for Working with Minors
                </a>
                .
              </li>
            </ul>
          </Section>
          <Section
            heading="
            Hunt Code of Conduct: Maintaining a Harassment-Free Environment
          "
          >
            <ul>
              <li>
                The MIT Mystery Hunt is dedicated to providing a harassment-free
                experience for everyone, regardless of gender, gender identity
                and expression, sexual orientation, disability, physical
                appearance, body size, age, race, or religion. We do not
                tolerate harassment of participants in any form. Participants
                asked to stop any harassing behavior are expected to comply
                immediately.
              </li>
              <li>
                MIT policies expressly prohibit harassment, including sexual
                harassment, sexual misconduct, gender-based harassment and
                stalking. All teams and participants must abide by{' '}
                <a href="https://policies.mit.edu/policies-procedures/90-relations-and-responsibilities-within-mit-community/94-harassment">
                  MIT's Harassment Policy
                </a>
                . Hunt participants violating this policy may be expelled from
                Mystery Hunt at the organizers' discretion.
              </li>
              <li>
                If you would like to report harassment, please remove yourself
                from the uncomfortable situation and contact Hunt HQ by email at{' '}
                <a href={'mailto:' + HQ_EMAIL}>{HQ_EMAIL}</a>. Alternatively,
                participants can report to MIT directly through{' '}
                <a href="https://idhr.mit.edu/reporting-options">
                  https://idhr.mit.edu/reporting-options
                </a>
                .
              </li>
              <li>
                Team captains should make sure this policy is understood by all
                team members and should actively discourage harassment within
                and among teams.
              </li>
            </ul>
          </Section>
        </div>
      </Section>
    </>
  );
};

export default HealthAndSafety;
