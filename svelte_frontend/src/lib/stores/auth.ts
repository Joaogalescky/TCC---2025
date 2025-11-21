import { writable } from 'svelte/store';
import { browser } from '$app/environment';

interface User {
	id: number;
	username: string;
	email: string;
	statusVotacao: boolean;
}

interface AuthState {
	user: User | null;
	token: string | null;
	isAuthenticated: boolean;
}

const initialState: AuthState = {
	user: null,
	token: browser ? localStorage.getItem('token') : null,
	isAuthenticated: false
};

export const auth = writable<AuthState>(initialState);

export const authActions = {
	login: (token: string, user: User) => {
		if (browser) {
			localStorage.setItem('token', token);
		}
		auth.set({ user, token, isAuthenticated: true });
	},
	
	logout: () => {
		if (browser) {
			localStorage.removeItem('token');
		}
		auth.set({ user: null, token: null, isAuthenticated: false });
	}
};