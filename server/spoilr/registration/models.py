from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from spoilr.core.models import Team, User


class TeamRegistrationInfo(models.Model):
    team = models.OneToOneField(Team, on_delete=models.CASCADE)
    locked = models.BooleanField(default=False)

    # This is saved on the Team model, so it must be unique
    team_name = models.CharField(verbose_name="Team Name", max_length=200, unique=True)

    contact_name = models.CharField(verbose_name="Primary Contact Name", max_length=200)
    contact_pronouns = models.CharField(
        verbose_name="Primary Contact Pronouns", max_length=50, default="", blank=True
    )
    contact_email = models.EmailField(verbose_name="Primary Contact E-mail")
    contact_phone = PhoneNumberField(
        region="US", verbose_name="Primary Contact Phone Number"
    )

    bg_bio = models.CharField(
        verbose_name="Team Bio", max_length=280, default="", blank=True
    )
    bg_emails = models.EmailField(
        verbose_name="Team-Wide Email List",
        max_length=500,
        default="",
        blank=True,
    )
    bg_playstyle = models.CharField(
        max_length=400,
        verbose_name="What describes your team's style of playing",
        choices=(
            ("fun", "We’re playing for fun!"),
            (
                "puzzles",
                "We’re pretty into puzzles but we’re not so focused on winning.",
            ),
            (
                "win",
                "We’re serious about solving. We really want to see the entire Hunt and maybe find the coin.",
            ),
        ),
        default="",
        blank=True,
    )
    bg_win = models.CharField(
        max_length=20,
        verbose_name="Is your team planning on winning the hunt?",
        choices=(("yes", "Yes"), ("no", "No"), ("unsure", "Unsure")),
        default="",
        blank=True,
    )
    bg_started = models.CharField(
        verbose_name="When was your team established?",
        max_length=200,
        default="",
        blank=True,
    )
    bg_location = models.CharField(
        verbose_name="Where are your team members located?",
        max_length=200,
        default="",
        blank=True,
    )
    bg_comm = models.CharField(
        verbose_name="What communication application will you be using to communicate with your team members while solving the MIT Mystery Hunt this year?",
        max_length=200,
        default="",
        blank=True,
    )
    bg_on_campus = models.CharField(
        verbose_name="Does your team plan to have an on-campus presence this year?",
        max_length=200,
        choices=(
            ("no", "No, we will be hunting remotely only"),
            ("yes", "Yes, we will have team members on campus"),
        ),
        default="",
        blank=True,
    )

    tb_room = models.CharField(
        max_length=400,
        verbose_name="Does your team need space at MIT for a team base during the Hunt?",
        choices=(
            ("no", "No, we already have a team base at or near MIT"),
            ("no_remote", "No, we will be hunting remotely only"),
            (
                "maybe",
                "We would like a room, but we have a backup plan in case Hunt is unable to secure a room",
            ),
            ("yes", "Yes, we absolutely need a room"),
        ),
        default="",
        blank=True,
    )
    tb_room_specs = models.CharField(
        verbose_name="If you are requesting a room, what specifications would you like for your team base? (E.g. specific rooms or room attributes)",
        max_length=500,
        default="",
        blank=True,
    )
    tb_location = models.CharField(
        verbose_name="If you are not requesting a classroom, where is your team base? We'll be visiting your team during the weekend. Do we need any special instructions to access your HQ? If remote, please provide instructions for how we can contact you virtually (e.g. Zoom link, Discord server, Google Meet, etc.)",
        max_length=500,
        default="",
        blank=True,
    )

    tm_total = models.IntegerField(
        verbose_name="How many people are on your team in total?",
        default=0,
        null=True,
        blank=True,
    )
    tm_last_year_total = models.IntegerField(
        verbose_name="How many people were on your team last year?",
        default=0,
        null=True,
        blank=True,
    )
    tm_undergrads = models.IntegerField(
        verbose_name="How many MIT undergraduates?", default=0, null=True, blank=True
    )
    tm_grads = models.IntegerField(
        verbose_name="How many MIT graduate students?", default=0, null=True, blank=True
    )
    tm_alumni = models.IntegerField(
        verbose_name="How many MIT alumni?", default=0, null=True, blank=True
    )
    tm_faculty = models.IntegerField(
        verbose_name="How many members from MIT faculty and staff?",
        default=0,
        null=True,
        blank=True,
    )
    tm_other = models.IntegerField(
        verbose_name="How many people are not affiliated with MIT?",
        default=0,
        null=True,
        blank=True,
    )
    tm_minors = models.IntegerField(
        verbose_name="How many minors (under 18 during Hunt)?",
        default=0,
        null=True,
        blank=True,
    )
    tm_onsite = models.IntegerField(
        verbose_name="How many people will your team have on campus",
        default=0,
        null=True,
        blank=True,
    )
    tm_offsite = models.IntegerField(
        verbose_name="How many remote solvers", default=0, null=True, blank=True
    )

    other_unattached = models.CharField(
        max_length=20,
        verbose_name="Are you willing to enlist unattached solvers?",
        choices=(("yes", "Yes"), ("no", "No")),
        default="",
        blank=True,
    )
    other_workshop = models.CharField(
        max_length=20,
        verbose_name="Would your team like to participate in the How to Hunt workshop prior to the event?",
        choices=(("yes", "Yes"), ("no", "No")),
        default="",
        blank=True,
    )
    other_puzzle_club = models.CharField(
        max_length=20,
        verbose_name="Do you have members from the MIT Puzzle Club on your team?",
        choices=(
            ("yes", "Yes"),
            ("no", "No"),
            ("already", "We already have someone from Puzzle Club on the team"),
        ),
        default="",
        blank=True,
    )
    other_how = models.CharField(
        max_length=20,
        verbose_name="How did you hear about the MIT Mystery Hunt?",
        choices=(
            ("past", "We’ve played in the past"),
            (
                "group",
                "Through a puzzle interest group (e.g. National Puzzlers’ League)",
            ),
            ("word-of-mouth", "Word of mouth from past participants or organizers"),
            ("social", "Through e-mail or social media"),
            ("puzzle-club", "Through the MIT Puzzle Club"),
            ("other", "Other"),
        ),
        default="",
        blank=True,
    )

    other = models.CharField(
        verbose_name="Anything else you’d like to share with us? Comments, questions, puns?",
        max_length=1500,
        default="",
        blank=True,
    )

    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.team_name


class IndividualRegistrationInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    contact_first_name = models.CharField(
        verbose_name="First name or nickname", max_length=200
    )
    contact_last_name = models.CharField(verbose_name="Last name", max_length=200)
    contact_pronouns = models.CharField(
        verbose_name="Pronouns", max_length=50, default="", blank=True
    )
    contact_email = models.EmailField(verbose_name="E-mail address")

    bg_mh_history = models.CharField(
        verbose_name="Have you participated in the MIT Mystery Hunt before? If so, tell us about your Hunt history!",
        max_length=500,
        default="",
        blank=True,
    )
    bg_other_history = models.CharField(
        verbose_name="Have you played in other puzzle-type events before? If so, feel free to give a short summary.",
        max_length=500,
        default="",
        blank=True,
    )
    bg_playstyle = models.CharField(
        max_length=400,
        verbose_name="What describes your style of playing?",
        choices=(
            (
                "fun",
                "I'm just playing for fun and would like to make some new friends.",
            ),
            (
                "puzzles",
                "I'm pretty into puzzles, but not so focused on winning.",
            ),
            (
                "win",
                "I'm a puzzle machine, and I'd love to be on a team that wants to find the coin. I really want to see the whole hunt.",
            ),
        ),
        default="",
        blank=True,
    )
    bg_other_prefs = models.CharField(
        verbose_name="Do you have any other preferences about what team you want to join?",
        max_length=500,
        default="",
        blank=True,
    )
    bg_under_18 = models.CharField(
        verbose_name="Are you under 18?",
        max_length=20,
        choices=(("yes", "Yes"), ("no", "No")),
        default="",
        blank=True,
    )
    bg_mit_connection = models.CharField(
        verbose_name="Are you connected to the MIT community? If so, how?",
        max_length=500,
        default="",
        blank=True,
    )
    bg_on_campus = models.CharField(
        verbose_name="Do you plan to participate on campus?",
        max_length=200,
        choices=(
            ("no", "No, I'll participate remotely"),
            ("maybe", "Maybe"),
            ("yes", "Yes, I'll be on campus"),
        ),
        default="",
        blank=True,
    )
    other = models.CharField(
        verbose_name="Anything else you’d like to share with us? Comments, questions, puns?",
        max_length=1500,
        default="",
        blank=True,
    )

    def __str__(self):
        return f"{self.contact_first_name} {self.contact_last_name}"
