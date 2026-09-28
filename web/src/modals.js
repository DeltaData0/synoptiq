/**
 * Dialog & Modal Management Component for Synoptiq.
 * Implements accessible, native <dialog> overlays with backdrop blur,
 * keyboard ESC dismissal, and click-outside light dismiss.
 */

import { renderReliabilityModalContent } from "./reliability_modal.js";

export function setupModals({ getEvaluationData }) {
  // Bind close buttons across all dialogs
  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modalId = btn.getAttribute("data-close-modal");
      closeModal(modalId);
    });
  });

  // Native dialog backdrop click-to-close
  document.querySelectorAll("dialog.app-modal").forEach((dialog) => {
    dialog.addEventListener("click", (e) => {
      const rect = dialog.getBoundingClientRect();
      const isInDialog = (
        rect.top <= e.clientY &&
        e.clientY <= rect.top + rect.height &&
        rect.left <= e.clientX &&
        e.clientX <= rect.left + rect.width
      );
      if (!isInDialog) {
        dialog.close();
      }
    });

    dialog.addEventListener("cancel", (e) => {
      // Standard ESC key triggers cancel
    });
  });

  return {
    openOperationalScope() {
      openModal("modal-operational-scope");
    },
    openFeatureArchitecture() {
      openModal("modal-feature-arch");
    },
    openCorpusDates() {
      openModal("modal-corpus-dates");
    },
    openReliability() {
      const modal = document.querySelector("#modal-reliability");
      if (modal) {
        renderReliabilityModalContent(modal, getEvaluationData?.());
      }
      openModal("modal-reliability");
    },
    closeModal(modalId) {
      closeModal(modalId);
    },
  };
}

function openModal(id) {
  const dialog = document.getElementById(id);
  if (dialog && typeof dialog.showModal === "function") {
    dialog.showModal();
    // Re-bind inner close buttons in case content was dynamically populated
    dialog.querySelectorAll("[data-close-modal]").forEach((btn) => {
      btn.onclick = () => dialog.close();
    });
  }
}

function closeModal(id) {
  const dialog = document.getElementById(id);
  if (dialog && dialog.open) {
    dialog.close();
  }
}
