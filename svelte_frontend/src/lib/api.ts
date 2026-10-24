import { env } from '$env/dynamic/public';

export const API_BASE = env.PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
	constructor(public status: number, message: string) {
		super(message);
	}
}

async function request(endpoint: string, options: RequestInit = {}) {
	const token = localStorage.getItem('token');
	
	const response = await fetch(`${API_BASE}${endpoint}`, {
		...options,
		headers: {
			'Content-Type': 'application/json',
			...(token && { Authorization: `Bearer ${token}` }),
			...options.headers
		}
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Network error' }));
		throw new ApiError(response.status, error.detail || 'Request failed');
	}

	return response.json();
}

export const api = {
	// Auth
	login: (email: string, password: string) => 
		fetch(`${API_BASE}/auth/token`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
			body: new URLSearchParams({ username: email, password })
		}).then(r => r.json()),

	register: (data: { username: string; email: string; password: string }) =>
		request('/users', {
			method: 'POST',
			body: JSON.stringify({ ...data, statusVotacao: false })
		}),

	getMe: () => request('/users/me'),

	// Elections
	getElections: () => request('/elections?limit=100'),
	getElectionCandidates: (id: number) => request(`/elections/${id}/candidates`),

	// Administração
	getUsers: () => request('/users?limit=100'),
	getCandidates: () => request('/candidates?limit=100'),
	setCandidate: (userId: number, isCandidate: boolean) =>
		request(`/users/${userId}/candidate`, {
			method: 'PATCH',
			body: JSON.stringify({ is_candidate: isCandidate })
		}),
	createElection: (title: string) =>
		request('/elections', {
			method: 'POST',
			body: JSON.stringify({ title })
		}),
	deleteElection: (id: number) => request(`/elections/${id}`, { method: 'DELETE' }),
	addCandidateToElection: (electionId: number, candidateId: number) =>
		request(`/elections/${electionId}/candidates/${candidateId}`, { method: 'POST' }),
	removeCandidateFromElection: (electionId: number, candidateId: number) =>
		request(`/elections/${electionId}/candidates/${candidateId}`, { method: 'DELETE' }),
	openElection: (id: number) => request(`/elections/${id}/open`, { method: 'POST' }),
	closeElection: (id: number) => request(`/elections/${id}/close`, { method: 'POST' }),
	tallyElection: (id: number) => request(`/elections/${id}/tally`, { method: 'POST' }),
	
	// Voting
	vote: (electionId: number, candidateId: number) =>
		request(`/vote/election/${electionId}`, {
			method: 'POST',
			body: JSON.stringify({ candidate_id: candidateId })
		}),

	getResults: (electionId: number) => request(`/vote/results/${electionId}`)
};