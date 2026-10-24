<script lang="ts">
	interface Props {
		status: string;
	}

	let { status }: Props = $props();

	const labels: Record<string, { text: string; classes: string }> = {
		draft: { text: "Em configuração", classes: "bg-gray-100 text-gray-700" },
		open: { text: "Aberta", classes: "bg-green-100 text-green-700" },
		closed: { text: "Encerrada", classes: "bg-yellow-100 text-yellow-800" },
		tallied: { text: "Apurada", classes: "bg-blue-100 text-blue-700" },
		cancelled: { text: "Cancelada", classes: "bg-red-100 text-red-700" },
	};

	let label = $derived(
		labels[status] ?? { text: status, classes: "bg-gray-100 text-gray-700" },
	);
</script>

<span class="text-xs font-medium px-2 py-0.5 rounded-full {label.classes}">
	{label.text}
</span>
