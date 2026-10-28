// TODO API: Replace these preview records with responses from the creator APIs.
// Dashboard preview data. Replace these records with creator API responses
// when authentication and the dashboard endpoints are connected.
export type ApplicantStatus = "Under Review" | "Selected" | "Rejected";
export type OpportunityStatus = "Open" | "In Progress" | "Draft" | "Completed";

export interface Opportunity {
  id: number;
  title: string;
  description: string;
  applications: number;
  status: OpportunityStatus;
  category: "digital" | "community" | "creative";
  location: string;
  deadline: string;
  expectedHours: number;
  compensation: string;
}

export interface Application {
  id: number;
  name: string;
  initials: string;
  email: string;
  opportunityId: number;
  appliedDate: string;
  status: ApplicantStatus;
  bio: string;
  skills: string[];
}

export const creatorProfile = {
  name: "Tech for Good",
  initials: "TG",
  email: "hello@techforgood.example",
  location: "Calgary, AB",
  description:
    "We help community organizations make a bigger impact through technology, creativity, and meaningful local opportunities.",
};

export const initialOpportunities: Opportunity[] = [
  {
    id: 1,
    title: "Social Media Support",
    description:
      "Help our community team plan engaging social posts and share the stories behind our local projects.",
    applications: 5,
    status: "Open",
    category: "digital",
    location: "Remote",
    deadline: "2026-11-12",
    expectedHours: 6,
    compensation: "$120 honorarium",
  },
  {
    id: 2,
    title: "Event Volunteer Support",
    description:
      "Welcome guests, help with setup, and support our volunteers at the next community technology workshop.",
    applications: 3,
    status: "Open",
    category: "community",
    location: "Calgary, AB",
    deadline: "2026-11-08",
    expectedHours: 5,
    compensation: "Volunteer · refreshments provided",
  },
  {
    id: 3,
    title: "Data Entry and Organization",
    description:
      "Organize community survey responses into a clear spreadsheet that helps our team plan future programs.",
    applications: 3,
    status: "Open",
    category: "digital",
    location: "Hybrid · Calgary, AB",
    deadline: "2026-11-15",
    expectedHours: 8,
    compensation: "$160 honorarium",
  },
  {
    id: 4,
    title: "Graphic Design",
    description:
      "Create a welcoming poster and simple social graphics for our community digital skills program.",
    applications: 1,
    status: "In Progress",
    category: "creative",
    location: "Remote",
    deadline: "2026-11-05",
    expectedHours: 10,
    compensation: "$200 honorarium",
  },
  {
    id: 5,
    title: "Community Website Updates",
    description:
      "Refresh program information and improve the accessibility of a local nonprofit's website.",
    applications: 0,
    status: "Draft",
    category: "digital",
    location: "Remote",
    deadline: "2026-11-25",
    expectedHours: 8,
    compensation: "$180 honorarium",
  },
];

export const initialApplications: Application[] = [
  {
    id: 1,
    name: "Sanjay Kumar",
    initials: "SK",
    email: "sanjay.kumar@example.com",
    opportunityId: 1,
    appliedDate: "2026-10-10",
    status: "Under Review",
    bio: "Marketing student who enjoys telling community stories and creating social content that brings people together.",
    skills: ["Social media", "Copywriting", "Canva"],
  },
  {
    id: 2,
    name: "Aisha Rahman",
    initials: "AR",
    email: "aisha.rahman@example.com",
    opportunityId: 3,
    appliedDate: "2026-10-08",
    status: "Selected",
    bio: "Detail-oriented business student with experience cleaning survey data and organizing spreadsheets for a campus club.",
    skills: ["Data entry", "Excel", "Organization"],
  },
  {
    id: 3,
    name: "Michael Lee",
    initials: "ML",
    email: "michael.lee@example.com",
    opportunityId: 2,
    appliedDate: "2026-10-05",
    status: "Rejected",
    bio: "Community volunteer interested in helping run accessible events and meeting people from across Calgary.",
    skills: ["Event setup", "Customer service", "Teamwork"],
  },
  {
    id: 4,
    name: "Priya Patel",
    initials: "PP",
    email: "priya.patel@example.com",
    opportunityId: 4,
    appliedDate: "2026-10-03",
    status: "Under Review",
    bio: "Visual communications student who makes clear, approachable designs for student groups and community projects.",
    skills: ["Graphic design", "Illustrator", "Canva"],
  },
  {
    id: 5,
    name: "Jordan Chen",
    initials: "JC",
    email: "jordan.chen@example.com",
    opportunityId: 1,
    appliedDate: "2026-10-02",
    status: "Selected",
    bio: "Emerging content creator with experience planning short campaigns for a university sustainability club.",
    skills: ["Photography", "Content planning", "Social media"],
  },
  {
    id: 6,
    name: "Olivia Thompson",
    initials: "OT",
    email: "olivia.thompson@example.com",
    opportunityId: 2,
    appliedDate: "2026-10-01",
    status: "Under Review",
    bio: "Friendly hospitality student who enjoys welcoming guests and making community activities run smoothly.",
    skills: ["Guest support", "Event setup", "Communication"],
  },
  {
    id: 7,
    name: "Noah Williams",
    initials: "NW",
    email: "noah.williams@example.com",
    opportunityId: 3,
    appliedDate: "2026-09-30",
    status: "Under Review",
    bio: "Computer science student looking to apply careful problem-solving and spreadsheet skills to a local project.",
    skills: ["Google Sheets", "Data entry", "Problem-solving"],
  },
  {
    id: 8,
    name: "Sofia Garcia",
    initials: "SG",
    email: "sofia.garcia@example.com",
    opportunityId: 1,
    appliedDate: "2026-09-29",
    status: "Under Review",
    bio: "Communications student who creates bilingual social content and enjoys highlighting local organizations.",
    skills: ["Copywriting", "Translation", "Social media"],
  },
  {
    id: 9,
    name: "Ethan Brooks",
    initials: "EB",
    email: "ethan.brooks@example.com",
    opportunityId: 1,
    appliedDate: "2026-09-28",
    status: "Rejected",
    bio: "Student photographer interested in building practical experience in digital storytelling and campaign design.",
    skills: ["Photography", "Photo editing", "Canva"],
  },
  {
    id: 10,
    name: "Amara Okafor",
    initials: "AO",
    email: "amara.okafor@example.com",
    opportunityId: 2,
    appliedDate: "2026-09-27",
    status: "Selected",
    bio: "Experienced campus volunteer who supports inclusive events and can help coordinate a small team on the day.",
    skills: ["Volunteer coordination", "Event setup", "Teamwork"],
  },
  {
    id: 11,
    name: "Liam Wilson",
    initials: "LW",
    email: "liam.wilson@example.com",
    opportunityId: 3,
    appliedDate: "2026-09-26",
    status: "Under Review",
    bio: "Economics student comfortable with spreadsheet formulas and turning survey responses into useful summaries.",
    skills: ["Excel", "Data organization", "Attention to detail"],
  },
  {
    id: 12,
    name: "Zara Ahmed",
    initials: "ZA",
    email: "zara.ahmed@example.com",
    opportunityId: 1,
    appliedDate: "2026-09-25",
    status: "Under Review",
    bio: "Creative student who designs simple social posts and wants to support organizations making a local difference.",
    skills: ["Canva", "Content planning", "Communication"],
  },
];

// Work totals are independent of opportunity count: one opportunity may have
// multiple contributors and completed work submissions.
export const summaryWork = { inProgress: 3, completed: 8 };
