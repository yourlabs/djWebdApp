et main (_, _ : nat * address) : operation list * address =
    let op, addr = Tezos.create_contract
        (fun (p, s : int * int) -> [], p + s)
        None
        0mutez
        1
    in
  ([op], addr)

// alias ligo="docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.54.1"
// ligo compile contract /tmp/simple_factory.mligo --protocol jakarta > simple_factory.tz
