import { env } from '$env/dynamic/public';

export const API_BASE = env.PUBLIC_API_URL || 'http://localhost:8000';

export interface VoteResult {
	message: string;
	// SHA-256 do voto cifrado; não revela em quem a pessoa votou
	receipt: string;
}

export interface ReceiptStatus {
	status: 'pending' | 'registered';
	lote: number | null;
}

export interface AuditReport {
	election_id: number;
	total_votos: number;
	lots: { numero_lote: number; qtd_votos: number; hash_lote: string; receipts: string[] }[];
	chain_valid: boolean;
}

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
	cancelElection: (id: number) => request(`/elections/${id}/cancel`, { method: 'POST' }),
	deleteUser: (id: number) => request(`/users/${id}`, { method: 'DELETE' }),
	reactivateUser: (id: number) => request(`/users/${id}/reactivate`, { method: 'POST' }),
	deleteElection: (id: number) => request(`/elections/${id}`, { method: 'DELETE' }),
	addCandidateToElection: (electionId: number, candidateId: number) =>
		request(`/elections/${electionId}/candidates/${candidateId}`, { method: 'POST' }),
	removeCandidateFromElection: (electionId: number, candidateId: number) =>
		request(`/elections/${electionId}/candidates/${candidateId}`, { method: 'DELETE' }),
	openElection: (id: number) => request(`/elections/${id}/open`, { method: 'POST' }),
	closeElection: (id: number) => request(`/elections/${id}/close`, { method: 'POST' }),
	tallyElection: (id: number) => request(`/elections/${id}/tally`, { method: 'POST' }),
	
	// Voting
	vote: (electionId: number, candidateId: number): Promise<VoteResult> =>
		request(`/vote/election/${electionId}`, {
			method: 'POST',
			body: JSON.stringify({ candidate_id: candidateId })
		}),

	checkReceipt: (electionId: number, receipt: string): Promise<ReceiptStatus> =>
		request(`/vote/receipt/${electionId}/${encodeURIComponent(receipt.trim())}`),

	getAudit: (electionId: number): Promise<AuditReport> =>
		request(`/elections/${electionId}/audit`),

	getResults: (electionId: number) => request(`/vote/results/${electionId}`)
};