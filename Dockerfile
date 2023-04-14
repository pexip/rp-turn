# run ansible inside the builder comtainer
ARG baseimage
FROM ${baseimage} as builder

# prerequisites
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y ansible git sudo systemctl
RUN useradd --create-home pexip

# run ansible
RUN --mount=type=bind,source=/,target=/run/rp-turn PYTHONUNBUFFERED=1 ansible-playbook /run/rp-turn/ansible.yml

# cleanup
RUN apt-get -y autoremove ansible git
RUN find /var/log /var/cache /var/lib/apt/lists -name "cracklib" -prune -o -type f -exec rm {} ';'

# export as a single layer
FROM scratch
COPY --from=builder / /
USER pexip
# TODO set entrypoint for standalone use
