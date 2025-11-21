const API_BASE = 'http://localhost:8000';

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

	// Elections
	getElections: () => request('/elections'),
	getElectionCandidates: (id: number) => request(`/elections/${id}/candidates`),
	
	// Voting
	vote: (electionId: number, candidateId: number) =>
		request(`/vote/election/${electionId}`, {
			method: 'POST',
			body: JSON.stringify({ candidate_id: candidateId })
		}),

	getResults: (electionId: number) => request(`/vote/results/${electionId}`)
};